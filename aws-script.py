import argparse


parser = argparse.ArgumentParser(description='Playing with AWS')
parser.add_argument('parameter', nargs='?', default='empty')
args = parser.parse_args()

if args.parameter == 'empty':

    print('I can tell that no argument was given and I can deal with that here.')
    print('Doing some stuff...')
    print('Doing some stuff...')
    print('Doing some stuff...')


elif args.parameter == 'start-http':
    print('Apache restarted')

else:
    print(args.parameter)