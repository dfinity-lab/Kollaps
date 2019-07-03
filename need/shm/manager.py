
from os import path
from time import sleep
from ctypes import CDLL, c_float, c_ulong, c_uint


def get_shared_lib_path():
    file_path = path.abspath(__file__)
    folder_path = "/".join(file_path.split('/')[0:-1])
    return folder_path + "/ManagerSharedMem.so"


def main():
    manager = CDLL(get_shared_lib_path())
    manager.init(1)

    manager.initDestination(c_uint(167772161), c_ulong(1234), c_float(0.1), c_float(0.2), c_float(0.3))

    input("M $ ")

    manager.tearDown()


if __name__ == '__main__':
    main()
