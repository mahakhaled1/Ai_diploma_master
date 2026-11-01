
def analyze_email(email):
    """
    Check email.
    Args:
        email (str): User email.
    Returns:
        None.
    """
    # check count "@"
    if email.count("@") != 1:
        print("Invalid email")
        return
    else:
        print("Valid email")
    # user name
    user_name = email.split("@")[0]
    # domain name
    domain_name = email.split("@")[1].rsplit(".", 1)[0]
    print("User name:", user_name)
    print("Domain name:", domain_name)
    # check domain type
    if email.endswith(".edu"):
        print("This is Educational Domain")
    elif email.endswith(".com"):
        print("This is Commercial Domain")
    else:
        print("Other Domain")

email = input("Enter the email: ")
analyze_email(email)