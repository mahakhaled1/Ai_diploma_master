def clean_message(message):
    """
    Clean message.

    Args:
        message (str): message to clean

    Returns:
        None
    """
    # clean message
    message = message.replace("#", "")
    message = message.replace("@", "")
    message = message.replace("!", "")
    message = message.replace("6789", "")
    words = message.split()
    print(words[0][::-1], words[1])


message = "###!!@mocleW EPGTQ!!!6789"
clean_message(message)