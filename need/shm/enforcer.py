
from os import path
from time import sleep
from ctypes import CDLL


def get_shared_lib_path():
    file_path = path.abspath(__file__)
    folder_path = "/".join(file_path.split('/')[0:-1])
    return folder_path + "/EnforcerSharedMem.so"


def main():
    enforcer = CDLL(get_shared_lib_path())
    enforcer.init()

    # input("E $ ")

    enforcer.pullChanges()

    enforcer.tearDown()



if __name__ == '__main__':
    main()
