from cc_lib import peripheral


def main():
    print("Version 0.1.0.dev4")
    print(peripheral.is_present("right"))
    print(peripheral.get_methods("right"))
