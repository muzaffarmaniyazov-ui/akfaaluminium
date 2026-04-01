from colorama import Fore



_banner = '''
 SWAGGER
'''



def banner(host, port):
    print(Fore.RED + _banner)
    print(f'http://{host}:{port}')