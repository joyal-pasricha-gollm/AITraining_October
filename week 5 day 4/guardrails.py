import re


def contains_pii(text):
    email = r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b"
    phone = r"\b[6-9]\d{9}\b"

    return bool(
        re.search(email, text)
        or re.search(phone, text)
    )
# if contains_pii(question):
#     print ("PII detected. Please remove personal contact details.")
#     break



def clean_output(answer):

    answer = re.sub(
        r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b",
        "[EMAIL REDACTED]",
        answer
    )

    answer = re.sub(
        r"\b[6-9]\d{9}\b",
        "[PHONE REDACTED]",
        answer
    )

    return answer