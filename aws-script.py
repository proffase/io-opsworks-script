#!/usr/bin/python3
import argparse


parser = argparse.ArgumentParser(description='Playing with AWS')
parser.add_argument('parameter', nargs='?', default='empty')
args = parser.parse_args()

if args.parameter == 'empty':
    
    import boto3
    import string
    import random
    import os
    import time
    import paramiko
    import select

    # Hardcoded values
    # key_pair_name = 'DennisF'
    existing_vpc = 'vpc-6440e402'
    zone_name = 'eu-west-1c'
    token_path = './token.txt'


    # Generate ASCII string for client token
    def generate_string(length=64):
        client_token = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
        return client_token


    # Checking if token file exists and previous operation is still running
    if os.path.isfile(token_path):
        while os.path.isfile(token_path):
            print('Previous operation is still runnning... wait a moment')
            time.sleep(5)
    else:
        # Save client token into file
        file = open(token_path, 'w')
        file.write(generate_string())
        file.close()

    if os.path.isfile(token_path) == False:
        file = open(token_path, 'w')
        file.write(generate_string())
        file.close()

    file = open(token_path, 'r')
    result = file.readline()
    file.close()


    #Generate key pair
    print('Creating key pair...')

    key_name = 'DennisKEY-' + generate_string(4)
    key_file_path = key_name + '.pem'

    ec2 = boto3.client('ec2')
    response = ec2.create_key_pair(KeyName=key_name)

    file = open(key_file_path, 'w')
    file.write(response['KeyMaterial'])
    file.close()

    print('Saved private key file: ', key_file_path)

    os.chmod(key_file_path, 0o700)

   
    # Boto start
    ec2 = boto3.resource('ec2')

    # Choose availability zone
    # zone = ec2.meta.client.describe_availability_zones()
    # print('Zone chosen:', zone['AvailabilityZones'][random.randint(0,1)]['ZoneName'])
    # zone_name = zone['AvailabilityZones'][random.randint(0,1)]['ZoneName']

    # Create EC2 instance
    print('Creating EC2 instance...')

    instances = ec2.create_instances(ImageId='ami-58d7e821',
                                        MinCount=1,
                                        MaxCount=1,
                                        KeyName=key_name,
                                        InstanceType='t2.micro',
                                        Placement={'AvailabilityZone':zone_name},
                                        ClientToken=result,
                                        TagSpecifications=[{'ResourceType': 'instance',
                                                            'Tags': [{
                                                                'Key': 'Name',
                                                                'Value': 'DennisF-' + generate_string(4)
                                                            }
                                                            ]
                                                            }
                                                        ],

                                        )

    instances[0].wait_until_running()
    print('EC2 instance successfully created, ec2_id =', instances[0].id)
    ec2_id = instances[0].id


    # Getting public IP of created instance
    instances[0].load()
    print('IP is:', instances[0].public_ip_address)
    ec2_ip_addr = instances[0].public_ip_address


    # Create security group
    print('Creating security group...')
    sg_name = 'Dennis-SG-' + ec2_id

    security_group = ec2.create_security_group(Description='DennisFGroup',
                                            GroupName=sg_name,
                                            VpcId=existing_vpc)
    security_group.authorize_ingress(
        IpPermissions=[
            {'IpProtocol': 'tcp',
            'FromPort': 80,
            'ToPort': 80,
            'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
            {'IpProtocol': 'tcp',
            'FromPort': 22,
            'ToPort': 22,
            'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
        ]
    )

    print('Security group successfully created, sg_id =', security_group.id)
    sg_id = security_group.id

    instance = ec2.Instance(ec2_id)
    response = instance.modify_attribute(Groups=[security_group.id])


    # Create EBS volume
    print('Creating volume...')
    volume = ec2.create_volume(AvailabilityZone=instance.placement['AvailabilityZone'],
                            Size=1,
                            VolumeType='standard',
                            TagSpecifications= [ {'ResourceType':'volume',
                            'Tags': [
                                {'Key': 'Name',
                                'Value': 'Dennis-' + ec2_id}
                            ]
                            }
                            ]
                            )

    vol_id = volume.volume_id
    print('Volume has been created, vol_id =', vol_id)

    while volume.state != 'available':
        time.sleep(3)
        volume.reload()
        # print(volume.state)

    print('Attaching volume...')
    attached = instance.attach_volume(VolumeId=vol_id, Device='/dev/sdz')
    print('Volume attached at:', attached['AttachTime'])


    # Deleting token file
    if os.path.isfile(token_path):
        os.remove(token_path)
    else:
        print('Error: cannot delete. Token file not found at:', token_path)



    key = paramiko.RSAKey.from_private_key_file(key_file_path)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    

    shell_commands = [
        'mkdir /home/ubuntu/mountpoint',
        'sudo chown ubuntu:ubuntu /home/ubuntu/mountpoint',
        'sudo apt update && sudo apt -y install apache2 git',
        'mkdir /home/ubuntu/mountpoint && cd /home/ubuntu/mountpoint && git init',
        'cd /home/ubuntu/mountpoint && git clone https://proffase@github.com/proffase/io-opsworks-script.git',
        'chmod 755 /home/ubuntu/mountpoint/io-opsworks-script/aws-script.py',
        'touch /home/ubuntu/outputfile.txt && python3 /home/ubuntu/mountpoint/io-opsworks-script/aws-script.py start > /home/ubuntu/outputfile.txt 2>&1'
    ]

    # Command mkfs is not working through paramiko
    # 'echo "sudo mkfs.ext4 /dev/xvdz" > /tmp/format.sh;chmod 755 format.sh;sudo /bin/sh format.sh',
    # 'mkdir /home/ubuntu/mountpoint && sudo mount /dev/xvdz /home/ubuntu/mountpoint'

    # Connect/ssh to an instance
    print('Running commands through SSH...')
    try:
        
        client.connect(hostname=ec2_ip_addr, username="ubuntu", pkey=key)

        for command in shell_commands:
            client.invoke_shell()
            stdin, stdout, stderr = client.exec_command(command)
            # exit_status = stdout.channel.recv_exit_status()
            # if exit_status == 0:
            #     print (command + '........OK')
            # else:
            #     print("Error", exit_status, stdin, stdout, stderr)
            while not stdout.channel.exit_status_ready():
                # Only print data if there is data to read in the channel
                if stdout.channel.recv_ready():
                    rl, wl, xl = select.select([stdout.channel], [], [], 0.0)
                    if len(rl) > 0:
                        # Print data from stdout
                        print(stdout.channel.recv(1024),)
            
            #print(stdout.read())
            #print(stderr.read())


        client.close()

    except Exception as e:
        print(e)

    print('Basic auth: username=user\npassword=password\nhttp output available at: http://{}/cgi-bin/script.cgi'.format(ec2_ip_addr))


elif args.parameter == 'start':
    import subprocess
    print('http starting...')

    result = subprocess.run('sudo touch /var/www/html/.htaccess', stdout=subprocess.PIPE, shell=True).stdout.decode('utf-8')
    # print(result)
    result = subprocess.run('cd /var/www/html && echo \'AuthType Basic\nAuthName "Restricted Content"\nAuthUserFile /var/www/.htpasswd\nRequire valid-user\' | sudo tee .htaccess', stdout=subprocess.PIPE, shell=True).stdout.decode('utf-8')
    # print(result)
    result = subprocess.run('sudo touch /var/www/.htpasswd', stdout=subprocess.PIPE, shell=True).stdout.decode('utf-8')
    # print(result)
    result = subprocess.run('cd /var/www && echo "user:\$apr1\$lo/vS5iP\$c8ZvIWj5Cd3C7Y24ByVBS0" | sudo tee .htpasswd', stdout=subprocess.PIPE, shell=True).stdout.decode('utf-8')
    # print(result)
    result = subprocess.run('sudo sed -i "/<Directory \/var\/www\/>/,\@</Directory>@ s/None/All/g" /etc/apache2/apache2.conf && sudo service apache2 restart', stdout=subprocess.PIPE, shell=True).stdout.decode('utf-8')
    # print(result)
    result = subprocess.run('sudo a2enmod cgi && sudo service apache2 restart', stdout=subprocess.PIPE, shell=True).stdout.decode('utf-8')
    # print(result)
    result = subprocess.run('sudo touch /usr/lib/cgi-bin/script.cgi && sudo chmod 755 /usr/lib/cgi-bin/script.cgi', stdout=subprocess.PIPE, shell=True).stdout.decode('utf-8')
    # print(result)
    result = subprocess.run('cd /usr/lib/cgi-bin && echo "#! /bin/bash\necho \'Content-Type: text/plain\'\necho\ncd /home/ubuntu/mountpoint/io-opsworks-script && git log -1 --stat\necho\nps -C apache2 -o %cpu,%mem,cmd" | sudo tee script.cgi', stdout=subprocess.PIPE, shell=True).stdout.decode('utf-8')
    # print(result)
    result = subprocess.run('cd /home/ubuntu/mountpoint/io-opsworks-script/.git/hooks && touch post-commit && chmod 755 post-commit', stdout=subprocess.PIPE, shell=True).stdout.decode('utf-8')
    result = subprocess.run('cd /home/ubuntu/mountpoint/io-opsworks-script/.git/hooks && echo "#!/bin/sh\nexec sudo systemctl restart apache2" | tee post-commit', stdout=subprocess.PIPE, shell=True).stdout.decode('utf-8')
else:
    print('Incorrect parameter:', args.parameter)