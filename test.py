#!/usr/bin/env python
def deco(callback):
    print 'In decorator'
    def func(*args, **kargs):
        print callback.func_name
        return callback(*args, **kargs)
    return func

@deco
def demo():
    print 'Hello World'

'''if __name__ == '__main__':
    demo()
'''
