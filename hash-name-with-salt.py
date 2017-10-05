# sha256 hash of a string
import hashlib
import re

# input verification
# https://docs.python.org/2/library/re.html#search-vs-match
while True:
    print('Input username')
    user =  input()
    if user[:3] == '/u/':
        print('Do not include "/u/"')
    m = re.search(r'[^A-Za-z0-9_-]', user)
    if m:
        print('Invalid character "'+str(m.group(0))+'"')
    else:
        break

# hash function
# http://pythoncentral.io/hashing-strings-with-python/
text = 'usernamehash+/u/' + user
textbytes = bytes(text, 'utf-8')
hash_object = hashlib.sha256(textbytes)
hex_dig = hash_object.hexdigest()
print('Hash of '+text+' is')
print(hex_dig)

# optional copy to clipboard
# https://stackoverflow.com/a/11063483
try:
    import pyperclip
    print('Copy hash to clipboard? y/n')
    yn = input()
    if yn.lower() == 'y':
        pyperclip.copy(hex_dig)
        print('Hash copied to clipboard')
except ImportError:
    pass