def to_wei(amount: float, decimals: int = 18) -> int:
	"""
    Converts an amount from ether to wei.

    Args:
        amount (float): The amount in ether.
        decimals (int, optional): The number of decimal places. Defaults to 18.

    Returns:
        int: The amount in wei.
    """
	return int(amount * (10 ** decimals))


def from_wei(amount: int, decimals: int = 18) -> float:
	"""
    Converts an amount from wei to ether.

    Args:
        amount (int): The amount in wei.
        decimals (int, optional): The number of decimal places. Defaults to 18.

    Returns:
        float: The amount in ether.
    """
	return amount / (10 ** decimals)
