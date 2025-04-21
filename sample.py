def karatsuba (x, y):
    # Base case for recursion
    if len(x) == 1 or len(y) == 1:
        return int(x) * int(y)

    # Calculate the size of the numbers
    max_len = max(len(x), len(y))
    half_len = max_len // 2

    # Split x and y into two halves
    x_high = x[:-half_len]
    x_low = x[-half_len:]
    y_high = y[:-half_len]
    y_low = y[-half_len:]

    # Recursively calculate three products
    z0 = karatsuba(x_low, y_low)
    z1 = karatsuba(str(int(x_low) + int(x_high)), str(int(y_low) + int(y_high)))
    z2 = karatsuba(x_high, y_high)

    # Combine the three products to get the final result
    return (z2 * (10 ** (2 * half_len))) + ((z1 - z2 - z0) * (10 ** half_len)) + z0
if __name__ == "__main__":
    A = "1456"
    B = "6533"

    # Multiply the large numbers A and B using the Karatsuba algorithm
    print(karatsuba(A, B))
