# App Reverse Engineering

This document is a log of the operations taken to decypher the protocol that the MagicSwitchBot follows, as the original documentation was unsufficient to get the commands return data read.

I followed [this guide](https://reverse-engineering-ble-devices.readthedocs.io/en/latest/protocol_reveng/00_protocol_reveng.html#android-application-analysis)

* **App Name**: MagicSwitchBot

* **Apk name**: com.runChina.moLiKaiGuan.apk

Once the code is decompiled, I could find no errors in what I am doing with the library.

I also used WireShark to sniff GATT protocol calls from the Android original APP and compare them with the commands that my library was sending.

That  led me to find that the encrypted values I was sending to the device were wite different from the ones that the APP sends. Decrypting with AES both values set I could determine that the key that the original documentation was showing was incorrect.

So, I looked for the key definition in the App and this is what I found:

```java
package com.runChina.moLiKaiGuan.bleMoudle;

import javax.crypto.Cipher;
import javax.crypto.spec.SecretKeySpec;

public class AESUtils {
    public static byte[] key = {42, 97, 57, 92, 64, 85, 73, 81, 58, 90, 75, 98, 27, 109, 55, 53};

    public static void main(String[] strArr) throws Exception {
    }

    public static byte[] encode(byte[] bArr, byte[] bArr2) {
        SecretKeySpec secretKeySpec = new SecretKeySpec(bArr, "AES");
        try {
            Cipher instance = Cipher.getInstance("AES/ECB/NoPadding");
            instance.init(1, secretKeySpec);
            return instance.doFinal(bArr2);
        } catch (Exception e) {
            e.printStackTrace();
            return null;
        }
    }

    public static byte[] encode(byte[] bArr) {
        return encode(key, bArr);
    }

    public static byte[] decode(byte[] bArr, byte[] bArr2) {
        SecretKeySpec secretKeySpec = new SecretKeySpec(bArr, "AES");
        try {
            Cipher instance = Cipher.getInstance("AES/ECB/NoPadding");
            instance.init(2, secretKeySpec);
            return instance.doFinal(bArr2);
        } catch (Exception e) {
            e.printStackTrace();
            return null;
        }
    }

    public static byte[] decode(byte[] bArr) {
        return decode(key, bArr);
    }
}

```

So we can see that the key that the App and the device are sharing is:

```python
[42, 97, 57, 92, 64, 85, 73, 81, 58, 90, 75, 98, 27, 109, 55, 53]
```

