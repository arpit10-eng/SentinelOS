# make a simple calculator
def add(x, y):
    return x + y    
def subtract(x, y):
    return x - y
def multiply(x, y):
    return x * y
def divide(x, y):
        return x / y
a=int(input("Enter first number: "))
b=int(input("Enter second number: "))
print("addition:", add(a, b))
print("subtraction:", subtract(a, b))
print("multiplication:", multiply(a, b))
if b != 0:
    print("division:", divide(a, b))
else:
    print("division: Cannot divide by zero")