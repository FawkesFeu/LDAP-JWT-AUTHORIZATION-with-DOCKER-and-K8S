from jose import jwe
import json

key = "Qw4r8v2n3x6z1p7s0b5c9e8d4f0g2h1j"
token = "eyJhbGciOiJkaXIiLCJlbmMiOiJBMjU2R0NNIn0..EtLWiCR0Mo2IFUfn.w_lex0TCECXMcEOOouqlZXJMKP606vnXXOyyKU6ujkKJsIwYyA.gbwrjpTl9vvuBcl8AFvK3g"

decrypted = jwe.decrypt(token, key.encode())
print(decrypted)
try:
    import json
    print(json.loads(decrypted.decode()))
except Exception as e:
    print("Not valid JSON:", e)