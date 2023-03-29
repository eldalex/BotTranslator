import time

def print_wakeup(name):
    # Use a breakpoint in the code line below to debug your script.
    print(f'Просыпайся, {name}')  # Press Ctrl+F8 to toggle the breakpoint.


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    for i in reversed(range(1,10)):
        print(f"спать осталось:{i}")
        time.sleep(1)
        print('test123456')
        print('test123456')
        print('test123456')
    print_wakeup('PyCharm')
    while True:
        time.sleep(1)


# See PyCharm help at https://www.jetbrains.com/help/pycharm/
