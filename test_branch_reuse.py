#!/usr/bin/env python3

# Test file for verifying branch reuse behavior
def hello():
    print("Hello from test file")

def add_numbers(a,b):
    return a+b

# This formatting will need black to fix spacing
if __name__=="__main__":
    result=add_numbers(1,2)
    print(f"Result: {result}")