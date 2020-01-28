# -*- coding: utf-8 -*-
# import keyring
import smtplib
import ssl
import __secret


def check_set(txt=None):
    # myEmailAddress = keyring.get_password("email", "address")
    # myEmailPassword = keyring.get_password("email", "password")
    myEmailAddress = __secret.address
    myEmailPassword = __secret.password
    if myEmailAddress is None or myEmailPassword is None:
        print("""Both __secret.address and __secret.password must be defined if
              you want email alarms.""")
        return False
    return True


def send_email(txt=None, domain='auto'):
    # myEmailAddress = keyring.get_password("email", "address")
    # myEmailPassword = keyring.get_password("email", "password")
    myEmailAddress = __secret.address
    myEmailPassword = __secret.password
    if domain == 'auto':
        domain = myEmailAddress.split("@")[-1]

    SERVER = "smtp." + domain
    PORT = 465  # for SSL
    FROM = myEmailAddress
    TO = [myEmailAddress]
    SUBJECT = "Alert from aquarium"
    TEXT = "Cannot read from Arduino!"
    message = "Subject: {0}\n\n{1}".format(
        SUBJECT, TEXT if txt is None else txt)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(host=SERVER, port=PORT, context=context) as server:
        server.login(FROM, myEmailPassword)
        server.sendmail(FROM, TO, message.encode('utf8'))


if __name__ == "__main__":
    send_email("test message")
