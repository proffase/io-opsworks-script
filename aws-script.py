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
    ip_addr = instances[0].public_ip_address


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


elif args.parameter == 'start-http':
    print('http start')

else:
    print(args.parameter)