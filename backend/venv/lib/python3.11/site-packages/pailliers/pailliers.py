"""
Minimal pure-Python implementation of
`Paillier's additively homomorphic cryptosystem \
<https://en.wikipedia.org/wiki/Paillier_cryptosystem>`__.
"""
from __future__ import annotations
from typing import Union, Optional, Tuple
import doctest
import math
import secrets
from egcd import egcd
from rabinmiller import rabinmiller

def _primes(bit_length: int) -> Tuple[int, int]:
    """
    Return a pair of distinct primes (each having the specified
    number of bits in its representation).

    >>> (p, q) = _primes(32)
    >>> p.bit_length() == q.bit_length() == 32
    True
    >>> math.gcd(p, q)
    1
    """
    (lower, upper) = (2 ** (bit_length - 1), (2 ** bit_length) - 1)
    difference = upper - lower
    (p, q) = (0, 0)
    while p <= lower or not rabinmiller(p):
        p = (secrets.randbelow(difference // 2) * 2) + lower + 1
    while p == q or q <= lower or not rabinmiller(q):
        q = (secrets.randbelow(difference // 2) * 2) + lower + 1

    return (p, q)

def _generator(modulus: int) -> int:
    """
    Return a generator modulo the supplied modulus.

    >>> g = _generator(17)
    >>> math.gcd(g, 17)
    1
    >>> {(g * i) % 17 for i in range(17)} == set(range(17))
    True
    """
    g = 0
    while g == 0 or math.gcd(g, modulus) != 1:
        g = secrets.randbelow(modulus)

    return g

class secret(Tuple[int, int, int, int]):
    """
    Wrapper class for a tuple of four integers that represents a secret key.

    >>> secret_key = secret(2048)
    >>> public_key = public(secret_key)
    >>> isinstance(secret_key, secret)
    True

    Any attempt to supply an argument that is of the wrong type or outside the
    supported range raises an exception.

    >>> secret('abc')
    Traceback (most recent call last):
      ...
    TypeError: bit length must be an integer
    >>> secret(0)
    Traceback (most recent call last):
      ...
    ValueError: bit length must be a positive integer
    """
    def __new__(cls, bit_length: int) -> secret:
        """
        Create a secret key instance using the supplied argument
        (instead of the inherited :obj:`tuple` constructor behavior).
        """
        if not isinstance(bit_length, int):
            raise TypeError('bit length must be an integer')

        if bit_length < 1:
            raise ValueError('bit length must be a positive integer')

        (p, q) = _primes(bit_length)
        n = p * q
        lam = ((p - 1) * (q - 1)) // math.gcd(p - 1, q - 1)
        g = None
        while g is None:
            g = _generator(n ** 2)
            # pylint: disable=unbalanced-tuple-unpacking
            (d, mu, _) = egcd((pow(g, lam, n ** 2) - 1) // n, n)
            if d != 1: # pragma: no cover # Highly unlikely to occur.
                g = None

        return tuple.__new__(cls, (lam, mu % n, n, g))

class public(Tuple[int, int]):
    """
    Wrapper class for a pair of integers that represents a public key.

    >>> public_key = public(secret(2048))
    >>> isinstance(public_key, public)
    True

    Any attempt to supply an argument that is of the wrong type or outside the
    supported range raises an exception.

    >>> public('abc')
    Traceback (most recent call last):
      ...
    TypeError: secret key required to create public key
    """
    def __new__(cls, secret_key: secret) -> public:
        """
        Create a public key instance using the supplied argument
        (instead of the inherited :obj:`tuple` constructor behavior).
        """
        if not isinstance(secret_key, secret):
            raise TypeError('secret key required to create public key')

        return tuple.__new__(cls, secret_key[2:])

class plain(int):
    """
    Wrapper class for an integer that represents a plaintext.

    >>> isinstance(plain(123), plain)
    True
    """

class cipher(int):
    """
    Wrapper class for an integer that represents a ciphertext.

    >>> secret_key = secret(2048)
    >>> public_key = public(secret_key)
    >>> c = encrypt(public_key, plain(123))
    >>> isinstance(c, cipher)
    True

    This class defines a number of special methods corresponding to arithmetic
    operations so that Python's built-in operators can be used when working
    with instances of this class. These operators will only work on instances
    of this class that have been constructed with a public key (which is the
    default behavior of the :obj:`encrypt` function).

    >>> decrypt(secret_key, c + c)
    246
    >>> decrypt(secret_key, 2 * c)
    246

    To facilitate the use of instances that do not maintain internal copies of
    the same public key (*e.g.*, in cases where memory constraints are an issue
    or ciphertexts are stored/communicated separately from key information),
    the :obj:`add` and :obj:`mul` functions can be used.

    >>> c = cipher(int(c), public_key=public_key)
    >>> decrypt(secret_key, c + c)
    246
    >>> n = int(c)
    >>> c = cipher(n) # This instance has no internal copy of a public key.
    >>> c + c
    Traceback (most recent call last):
      ...
    ValueError: public key is required for addition
    >>> decrypt(secret_key, add(public_key, c, c))
    246
    >>> decrypt(secret_key, mul(public_key, c, 2))
    246

    **Warning:** When the true integer sum of two encrypted values --- or the
    true product of an encrypted value and an integer scalar --- exceeds the
    modulus within the public key, the decrypted result will not match the true
    result.

    >>> secret_key = secret(8)
    >>> public_key = public(secret_key)
    >>> c = encrypt(public_key, 2 ** 7)
    >>> int(decrypt(secret_key, c)) == 2 ** 7
    True
    >>> int(decrypt(secret_key, c * (2 ** 9))) == (2 ** 7) * (2 ** 9)
    False

    Any attempt to invoke the constructor using arguments that do not have the
    expected types raises an exception.

    >>> cipher('abc', public_key='abc')
    Traceback (most recent call last):
      ...
    ValueError: invalid literal for int() with base 10: 'abc'
    >>> cipher(123, public_key='abc')
    Traceback (most recent call last):
      ...
    TypeError: public key must be an instance of the public class
    """
    def __new__(
            cls: type,
            integer: int, # pylint: disable=unused-argument
            public_key: Optional[public] = None
        ):
        instance = int.__new__(cls, integer)

        if public_key is not None:
            if not isinstance(public_key, public):
                raise TypeError(
                    'public key must be an instance of the public class'
                )

            instance._public_key = public_key

        return instance

    def __add__(self: cipher, other: cipher) -> cipher:
        """
        Perform addition of encrypted values to produce the encrypted
        result.

        >>> secret_key = secret(2048)
        >>> public_key = public(secret_key)
        >>> c = encrypt(public_key, 22)
        >>> d = encrypt(public_key, 33)
        >>> r = c + d
        >>> int(decrypt(secret_key, r))
        55

        At least one of the two arguments must have a public key.

        >>> decrypt(secret_key, cipher(int(c)) + c)
        44
        >>> decrypt(secret_key, c + cipher(int(c)))
        44
        >>> cipher(int(c)) + cipher(int(c))
        Traceback (most recent call last):
          ...
        ValueError: public key is required for addition

        If public keys are specified in both ciphertexts, they must match.

        >>> secret_key_a = secret(2048)
        >>> public_key_a = public(secret_key_a)
        >>> secret_key_b = secret(2048)
        >>> public_key_b = public(secret_key_b)
        >>> encrypt(public_key_a, 123) + encrypt(public_key_b, 456)
        Traceback (most recent call last):
          ...
        ValueError: public keys of ciphertexts must match
        """
        public_key = None

        if hasattr(self, '_public_key'):
            public_key = self._public_key

        if hasattr(other, '_public_key'):
            if public_key is None:
                public_key = other._public_key
            elif tuple(public_key) != tuple(other._public_key):
                raise ValueError('public keys of ciphertexts must match')

        if public_key is None:
            raise ValueError('public key is required for addition')

        ciphertext = add(public_key, self, other)
        ciphertext._public_key = public_key
        return ciphertext

    def __radd__(self: cipher, other: Union[int, cipher]) -> cipher:
        """
        This method makes it possible to use the built-in :obj:`sum` function.

        >>> secret_key = secret(2048)
        >>> public_key = public(secret_key)
        >>> c = encrypt(public_key, 22)
        >>> decrypt(secret_key, sum([c, c, c, c]))
        88

        This method should not be invoked for any other reason.

        >>> 123 + c
        Traceback (most recent call last):
          ...
        TypeError: can only add ciphertexts
        """
        if isinstance(other, int) and other == 0:
            return self

        return self.__add__(other) # Default behavior.

    def __iadd__(self: cipher, other: cipher) -> cipher:
        """
        Add an encrypted value to an existing encrypted value.

        >>> secret_key = secret(2048)
        >>> public_key = public(secret_key)
        >>> c = encrypt(public_key, 22)
        >>> d = encrypt(public_key, 33)
        >>> c += d
        >>> int(decrypt(secret_key, c))
        55
        
        At least one of the two arguments must have a public key.

        >>> c += cipher(int(c))
        >>> decrypt(secret_key, c)
        110
        >>> d = cipher(int(d))
        >>> d += c
        >>> decrypt(secret_key, d)
        143
        >>> d = cipher(int(d))
        >>> d += cipher(int(c))
        Traceback (most recent call last):
          ...
        ValueError: public key is required for addition

        An integer base value can be used when accumulating iteratively.

        >>> b = 0
        >>> b += encrypt(public_key, 1)
        >>> b += encrypt(public_key, 2)
        >>> b += encrypt(public_key, 3)
        >>> decrypt(secret_key, b)
        6
        """
        return self.__add__(other)

    def __mul__(self: cipher, scalar: int) -> cipher:
        """
        Perform multiplication of an encrypted value by a scalar to produce
        the encrypted result.

        >>> secret_key = secret(2048)
        >>> public_key = public(secret_key)
        >>> c = encrypt(public_key, 22)
        >>> r = c * 3
        >>> int(decrypt(secret_key, r))
        66

        This instance must have a public key.

        >>> c = cipher(int(c))
        >>> c * 3
        Traceback (most recent call last):
          ...
        ValueError: public key is required for scalar multiplication
        """
        if not hasattr(self, '_public_key'):
            raise ValueError(
                'public key is required for scalar multiplication'
            )

        ciphertext = mul(self._public_key, self, scalar)
        setattr(ciphertext, '_public_key', self._public_key)
        return ciphertext

    def __rmul__(self: cipher, scalar: int) -> cipher:
        """
        Perform multiplication of an encrypted value by a scalar (that appears
        on the left side of the operator) to produce the encrypted result.

        >>> secret_key = secret(2048)
        >>> public_key = public(secret_key)
        >>> c = encrypt(public_key, 22)
        >>> r = 3 * c
        >>> int(decrypt(secret_key, r))
        66

        This instance must have a public key.

        >>> c = cipher(int(c))
        >>> c * 3
        Traceback (most recent call last):
          ...
        ValueError: public key is required for scalar multiplication
        """
        return self.__mul__(scalar)

    def __imul__(self: cipher, scalar: int) -> cipher:
        """
        Perform multiplication of an encrypted value by a scalar.

        >>> secret_key = secret(2048)
        >>> public_key = public(secret_key)
        >>> c = encrypt(public_key, 22)
        >>> c *= 3
        >>> int(decrypt(secret_key, c))
        66

        This instance must have a public key.

        >>> c = cipher(int(c))
        >>> c * 3
        Traceback (most recent call last):
          ...
        ValueError: public key is required for scalar multiplication
        """
        return self.__mul__(scalar)

def encrypt(public_key: public, plaintext: Union[plain, int]) -> cipher:
    """
    Encrypt the supplied plaintext using the supplied public key.

    >>> secret_key = secret(2048)
    >>> public_key = public(secret_key)
    >>> c = encrypt(public_key, 123)
    >>> isinstance(c, cipher)
    True

    Any attempt to invoke this function using arguments that do not have the
    expected types raises an exception.

    >>> encrypt(secret_key, 123)
    Traceback (most recent call last):
      ...
    TypeError: can only encrypt using a public key
    """
    if not isinstance(public_key, public):
        raise TypeError('can only encrypt using a public key')

    (n, g) = public_key
    r = _generator(n)
    ciphertext = cipher(
        (
            pow(g, plaintext % n, n ** 2)
            *
            pow(r, n, n ** 2)
        )
        %
        (n ** 2)
    )
    setattr(ciphertext, '_public_key', public_key)
    return ciphertext

def decrypt(secret_key: secret, ciphertext: cipher) -> plain:
    """
    Decrypt the supplied plaintext using the supplied secret key.

    >>> secret_key = secret(2048)
    >>> public_key = public(secret_key)
    >>> c = encrypt(public_key, 123)
    >>> decrypt(secret_key, c)
    123

    Any attempt to invoke this function using arguments that do not have the
    expected types raises an exception.

    >>> decrypt(public_key, c)
    Traceback (most recent call last):
      ...
    TypeError: can only decrypt using a secret key
    >>> decrypt(secret_key, 123)
    Traceback (most recent call last):
      ...
    TypeError: can only decrypt a ciphertext
    """
    if not isinstance(secret_key, secret):
        raise TypeError('can only decrypt using a secret key')

    if not isinstance(ciphertext, cipher):
        raise TypeError('can only decrypt a ciphertext')

    (lam, mu, n, _) = secret_key
    return plain((((pow(ciphertext, lam, n ** 2) - 1) // n) * mu) % n)

def add(public_key: public, *ciphertexts: cipher) -> cipher:
    """
    Perform addition of encrypted values to produce the encrypted
    result.

    >>> secret_key = secret(2048)
    >>> public_key = public(secret_key)
    >>> c = encrypt(public_key, 22)
    >>> d = encrypt(public_key, 33)
    >>> r = add(public_key, c, d)
    >>> int(decrypt(secret_key, r))
    55

    This function supports one or more ciphertexts. If only one ciphertext
    is supplied, that same ciphertext is returned.

    >>> x = encrypt(public_key, 4)
    >>> y = encrypt(public_key, 5)
    >>> z = encrypt(public_key, 6)
    >>> r = add(public_key, x, y, z)
    >>> int(decrypt(secret_key, r))
    15
    >>> r = add(public_key, x)
    >>> int(decrypt(secret_key, r))
    4

    Iterables of ciphertexts can be provided with the help of unpacking via
    ``*`` (thus allowing this function to be used in a manner that resembles
    the way that the built-in :obj:`sum` function can be used).

    >>> r = add(public_key, *(c for c in [x, y, z]))
    >>> int(decrypt(secret_key, r))
    15

    Any attempt to invoke this function using arguments that do not have the
    expected types raises an exception.

    >>> add(secret_key, c, d)
    Traceback (most recent call last):
      ...
    TypeError: can only perform operation using a public key
    >>> add(public_key, c, 123)
    Traceback (most recent call last):
      ...
    TypeError: can only add ciphertexts
    >>> add(public_key)
    Traceback (most recent call last):
      ...
    ValueError: at least one ciphertext is required
    """
    if not isinstance(public_key, public):
        raise TypeError('can only perform operation using a public key')

    if len(ciphertexts) < 1:
        raise ValueError('at least one ciphertext is required')

    modulus: int = public_key[0] ** 2
    ciphertexts = iter(ciphertexts)
    result = int(next(ciphertexts))
    for ciphertext in ciphertexts:
        if not isinstance(ciphertext, cipher):
            raise TypeError('can only add ciphertexts')
        result = (result * int(ciphertext)) % modulus

    return cipher(result)

def mul(public_key: public, ciphertext: cipher, scalar: int) -> cipher:
    """
    Perform multiplication of an encrypted value by a scalar to produce
    the encrypted result.

    >>> secret_key = secret(2048)
    >>> public_key = public(secret_key)
    >>> c = encrypt(public_key, 22)
    >>> r = mul(public_key, c, 3)
    >>> int(decrypt(secret_key, r))
    66

    Any attempt to invoke this function using arguments that do not have the
    expected types raises an exception.

    >>> mul(secret_key, c, 3)
    Traceback (most recent call last):
      ...
    TypeError: can only perform operation using a public key
    >>> mul(public_key, 123, 3)
    Traceback (most recent call last):
      ...
    TypeError: can only multiply a ciphertext
    >>> mul(public_key, c, 'abc')
    Traceback (most recent call last):
      ...
    TypeError: can only multiply by an integer scalar
    """
    if not isinstance(public_key, public):
        raise TypeError('can only perform operation using a public key')

    if not isinstance(ciphertext, cipher):
        raise TypeError('can only multiply a ciphertext')

    if not isinstance(scalar, int):
        raise TypeError('can only multiply by an integer scalar')

    return cipher(pow(int(ciphertext), scalar, public_key[0] ** 2))

if __name__ == '__main__':
    doctest.testmod() # pragma: no cover
