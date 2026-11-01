def clean_message(message):
    """
    Clean message.
    Args:
        message (str): message to clean
    Returns:
        None
    """
    message = message.replace("#", "")
    message = message.replace("$", "")
    message = message.replace("@", "")
    message = message.replace("!", "")
    message = message.replace("*", "")
    message = message.replace("9887", "")
    text = message.split()
    first_text = text[0][::-1]
    second_text = text[1]
    second_text = second_text.replace("E", "A")
    second_text = second_text.replace("U", "O")
    print(first_text, second_text)

message = "##$$$@!yalpstcejorp EPUVT****9887"
clean_message(message)