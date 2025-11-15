"""
Money handling with MICRONS pattern.

CRITICAL: All cost calculations use MICRONS (1 EUR = 1,000,000 micros).
Never use floats for money. Always use integer arithmetic.
Database stores BIGINT for all cost fields.

This prevents floating-point precision issues and ensures exact cost tracking.
"""

from typing import Union


# Constant: 1 EUR = 1,000,000 MICRONS
MICRONS_PER_EUR = 1_000_000


class Money:
    """
    Immutable money type using MICRONS (integer-based currency).

    1 EUR = 1,000,000 micros

    Always stores value as integer micros internally. Provides conversion
    methods for display and input.

    Examples:
        >>> m = Money.from_eur(1.50)
        >>> m.micros
        1500000
        >>> m.to_eur()
        1.5
        >>> m.format()
        '€1.50'
    """

    __slots__ = ('_micros',)

    def __init__(self, micros: int) -> None:
        """
        Create Money from micros value.

        Args:
            micros: Integer amount in micros (1 EUR = 1,000,000 micros)

        Raises:
            TypeError: If micros is not an integer
            ValueError: If micros is negative
        """
        if not isinstance(micros, int):
            raise TypeError(f"Money micros must be int, got {type(micros).__name__}")
        if micros < 0:
            raise ValueError(f"Money micros cannot be negative, got {micros}")

        self._micros = micros

    @property
    def micros(self) -> int:
        """Get the value in micros."""
        return self._micros

    @classmethod
    def from_eur(cls, eur: Union[int, float]) -> "Money":
        """
        Create Money from EUR amount.

        Args:
            eur: Amount in EUR (can be int or float)

        Returns:
            Money instance

        Examples:
            >>> Money.from_eur(1.50).micros
            1500000
            >>> Money.from_eur(0.001).micros
            1000
        """
        micros = int(round(eur * MICRONS_PER_EUR))
        return cls(micros)

    @classmethod
    def zero(cls) -> "Money":
        """Create Money with zero value."""
        return cls(0)

    def to_eur(self) -> float:
        """
        Convert to EUR (float).

        WARNING: Use only for display. Never use for calculations.

        Returns:
            Amount in EUR as float
        """
        return self._micros / MICRONS_PER_EUR

    def format(self, currency_symbol: str = "€") -> str:
        """
        Format money for display.

        Args:
            currency_symbol: Currency symbol to use (default: €)

        Returns:
            Formatted string like "€1.50"

        Examples:
            >>> Money(1500000).format()
            '€1.50'
            >>> Money(1234567).format("EUR")
            'EUR1.23'
        """
        eur = self.to_eur()
        return f"{currency_symbol}{eur:.2f}"

    def __add__(self, other: "Money") -> "Money":
        """Add two Money values."""
        if not isinstance(other, Money):
            return NotImplemented
        return Money(self._micros + other._micros)

    def __sub__(self, other: "Money") -> "Money":
        """Subtract two Money values."""
        if not isinstance(other, Money):
            return NotImplemented
        return Money(self._micros - other._micros)

    def __mul__(self, factor: int) -> "Money":
        """Multiply Money by integer factor."""
        if not isinstance(factor, int):
            return NotImplemented
        return Money(self._micros * factor)

    def __rmul__(self, factor: int) -> "Money":
        """Multiply Money by integer factor (reversed)."""
        return self.__mul__(factor)

    def __truediv__(self, divisor: int) -> "Money":
        """Divide Money by integer divisor."""
        if not isinstance(divisor, int):
            return NotImplemented
        if divisor == 0:
            raise ZeroDivisionError("Cannot divide Money by zero")
        return Money(self._micros // divisor)

    def __eq__(self, other: object) -> bool:
        """Check equality."""
        if not isinstance(other, Money):
            return NotImplemented
        return self._micros == other._micros

    def __lt__(self, other: "Money") -> bool:
        """Check less than."""
        if not isinstance(other, Money):
            return NotImplemented
        return self._micros < other._micros

    def __le__(self, other: "Money") -> bool:
        """Check less than or equal."""
        if not isinstance(other, Money):
            return NotImplemented
        return self._micros <= other._micros

    def __gt__(self, other: "Money") -> bool:
        """Check greater than."""
        if not isinstance(other, Money):
            return NotImplemented
        return self._micros > other._micros

    def __ge__(self, other: "Money") -> bool:
        """Check greater than or equal."""
        if not isinstance(other, Money):
            return NotImplemented
        return self._micros >= other._micros

    def __repr__(self) -> str:
        """Developer representation."""
        return f"Money({self._micros})"

    def __str__(self) -> str:
        """User-friendly string."""
        return self.format()

    def __hash__(self) -> int:
        """Hash for use in sets/dicts."""
        return hash(self._micros)


def micros_to_eur(micros: int) -> float:
    """
    Convert micros to EUR (float).

    WARNING: Use only for display. Never use for calculations.

    Args:
        micros: Amount in micros

    Returns:
        Amount in EUR as float

    Examples:
        >>> micros_to_eur(1500000)
        1.5
    """
    return micros / MICRONS_PER_EUR


def eur_to_micros(eur: Union[int, float]) -> int:
    """
    Convert EUR to micros (integer).

    Args:
        eur: Amount in EUR

    Returns:
        Amount in micros as integer

    Examples:
        >>> eur_to_micros(1.50)
        1500000
        >>> eur_to_micros(0.001)
        1000
    """
    return int(round(eur * MICRONS_PER_EUR))
