def clean_message(message):
    """
    Clean message.
    Args:
        message (str): message to clean
    Returns:
        None
    """
    # clean message
    message = message.replace("&", "")
    message = message.replace("@", "")
    message = message.replace("!", "")
    message= message.replace("$","")
    message= message.replace("*","")
    message = message.replace("1234", "")
    text= message.split()
    first_text=text[0][::-1]
    second_text=text[1]
    second_text=second_text.replace("I","E")
    second_text=second_text.replace("O","U")
    print(first_text,second_text)
    
message = "&&&**$gnirtS PLIO!!@1234"
clean_message(message)