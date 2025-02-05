
"""Combine two CSS themes into one, using @media to switch between the two.

# Overview

This script provides a CLI application for combining two CSS themes into one,
by splitting out the unique parts of the two themes into variables, then using
the `@media (prefers-color-scheme: ... )` block to switch between which
variables are currently active. Useful for generating a CSS sheet that
supports both light and dark mode.

# Author

https://smhk.net/pure-css-dark-mode-support-for-code-highlighting

# Version

v1.0.0

# Usage

Run:

```
python css_combine.py --prefix=blah --css-light=github-light.css --css-dark=github-dark.css
```

Will output `combined.css` in the same directory.

# Includes

* `CssSelector`, `CssProperty`, `CssRule` & `CssData`:
    - Dataclasses to store the parsed CSS.
* `CssParserState` & `CssParser`:
    - A simple CSS parser.
* `CssSheet`:
    - Building upon `CssData`, a class that provides methods for operating on
      the CSS data using set logic. This enables the separation of the unique
      parts of the stylesheets, and the recombination into a template using
      CSS variables.
* `combine_themes`:
    - A function that uses the CSS set logic provided by `CssSheet` to take
      two stylesheets and combine them.
* `main`:
    - The entrypoint, a basic CLI.

# Dependencies

This script has been tested on Python 3.12.2.

This script only imports from the Python standard library.

# Testing

Unit tests are provided in this file. They can be run using pytest, e.g.:

```
pytest css_combine.py
```

"""

import argparse
import copy
import itertools
import logging
from dataclasses import dataclass, field
from enum import Enum, auto


logger = logging.getLogger(__name__)


@dataclass
class CssSelector:
    """CSS selector.

    :param name: Selector name, e.g. ".something".
    """

    name: str

    def __str__(self):
        return f"CssSelector(name={self.name})"


@dataclass
class CssProperty:
    """CSS property.

    :param name: Property name, e.g. "background-color".
    :param value: Property value, e.g. "#FFFFFF".
    """

    name: str
    value: str

    def __str__(self):
        return f"CssProperty(name={self.name}, value={self.value})"


@dataclass
class CssRule:
    """CSS rule.

    Typically a CSS rule is identified by one or more selectors, which have
    one or more properties. However, no minimum is enforced.

    :param selectors: The selectors which identify this rule.
    :param properties: The properties which this rule has.
    """

    selectors: list[CssSelector] = field(default_factory=list)
    properties: list[CssProperty] = field(default_factory=list)

    def __str__(self):
        return f"CssRule(selectors={self.selectors}, properties={self.properties})"


class CssData:
    def __init__(self, rules: list[CssRule] | None = None):
        """CSS data.

        :param rules: (Optional) The CSS rules.
        """
        self.rules: list[CssRule] = [] if rules is None else rules

    def __str__(self):
        """Convert to string by printing out each rule."""
        return "\n".join(f"{str(rule)}" for rule in self.rules)

    @classmethod
    def from_str(cls, css_str: str) -> "CssData":
        """Create a new `CssData` from a string. The string should contain
        CSS.

        :param css_str: The string to read.
        :returns: A new `CssData` object.
        """
        return CssParser().parse(css_str)

    @classmethod
    def from_file(cls, filename) -> "CssData":
        """Create a new `CssData` from file. The file should contain CSS.

        :param filename: The file to read.
        :returns: A new `CssData`.
        """
        with open(filename, "r") as handle:
            return cls.from_str("".join(handle.readlines()))

    def has_property(
        self,
        selectors: list[CssSelector],
        prop: CssProperty,
        compare_value: bool = True,
    ) -> bool:
        """Whether the sheet contains the property for the given selectors.

        :param selectors: List of selectors to look up.
        :param prop: The property to look up.
        :param compare_value: If `True`, also compare the property value.
        :return: Whether the sheet contains the property for the given
            selectors, and if `compare_value`, whether the value matches.
        """
        for rule in self.rules:
            if rule.selectors == selectors:
                for this_prop in rule.properties:
                    if this_prop.name == prop.name:
                        if compare_value:
                            if this_prop.value == prop.value:
                                return True
                        else:
                            return True
        return False

    def append_property(self, selectors: list[CssSelector], prop: CssProperty):
        """Append a property to an existing rule if possible, else create a
        new rule with that property.

        :param selectors: List of selectors to use for rule.
        :param prop: The property to add to the selectors.
        """
        for rule in self.rules:
            if rule.selectors == selectors:
                rule.properties.append(prop)
                return
        self.rules.append(CssRule(selectors=selectors, properties=[prop]))


class CssParserState(Enum):
    """States for the `CssParser` state machine."""

    ROOT = auto()
    ROOT_COMMENT = auto()
    SELECTOR = auto()
    BLOCK = auto()
    BLOCK_COMMENT = auto()
    BLOCK_PROP_NAME = auto()
    BLOCK_GAP = auto()
    BLOCK_PROP_VALUE = auto()


class CssParser:
    def __init__(self):
        """A minimum viable CSS parser, implemented as a state machine, with
        no error handling.
        """
        self._reset_everything()

    def _reset_everything(self):
        """Reset all variables to initial state."""
        self.state: CssParserState = CssParserState.ROOT
        self.new_sheet: CssSheet = CssSheet()
        self.css_selector_reset()
        self.css_rule_reset()
        self.css_property_reset()

    def css_selector_reset(self):
        """Reset the selector name currently being built."""
        logger.debug("resetting selector")
        self.selector_name: list[str] = []

    def css_selector_name_grow(self, c: str):
        """Add one character to the selector name currently being built.

        :param c: Character to add to selector name.
        """
        self.selector_name.append(c)

    def css_selector_finish(self):
        """The selector name has been finished. Create the selector and add it
        to the list of selectors.
        """
        selector = CssSelector(name="".join(self.selector_name))
        logger.debug("appending selector: %s", selector)
        self.selectors.append(selector)
        self.css_selector_reset()

    def css_property_reset(self):
        """Reset the property name and value currently being built."""
        logger.debug("resetting properties")
        self.prop_name: list[str] = []
        self.prop_value: list[str] = []

    def css_property_name_grow(self, c: str):
        """Add one character to the property name currently being built.

        :param c: Character to add to property name.
        """
        self.prop_name.append(c)

    def css_property_value_grow(self, c: str):
        """Add one character to the property value currently being built.

        :param c: Character to add to property value.
        """
        self.prop_value.append(c)

    def css_property_finish(self):
        """The property name and value have been finished. Create the property
        and add it to the list of properties.

        NOTE: Property values keep being appended until a closing brace or
        semicolon is found, which means they may have unwanted trailing
        whitespace. For example:
        >>> "{ font-weight: bold }"
        Would lead to a value of:
        >>> "bold "
        This is removed with rstrip, resulting in:
        >>> "bold"
        """
        if self.prop_name:
            name = "".join(self.prop_name)
            value = "".join(self.prop_value).rstrip()
            prop = CssProperty(
                name=name,
                value=value,
            )
            logger.debug("appending property: %s", prop)
            self.properties.append(prop)
        else:
            logger.debug("not appending blank property")
        self.css_property_reset()

    def css_rule_reset(self):
        """Reset the rule currently being built."""
        logger.debug("resetting rules")
        self.selectors: list[CssSelector] = []
        self.properties: list[CssProperty] = []

    def css_rule_finish(self):
        """The rule has been finished. Create the rule and add it to the list
        of rules.
        """
        rule = CssRule(
            selectors=self.selectors,
            properties=self.properties,
        )
        logger.debug("appending rule: %s", rule)
        self.new_sheet.rules.append(rule)
        self.css_rule_reset()

    def state_change(self, new_state: CssParserState):
        """Change state of the FSM.

        :param new_state: The new state of the FSM.
        """
        logger.debug("changing state: %s -> %s", self.state, new_state)
        self.state = new_state

    def parse(self, css_str: str) -> "CssSheet":
        """Parse the CSS string using a simple FSM.

        :param css_str: The CSS string to parse.
        :returns: The CSS string parsed into a `CssSheet` object.
        """
        self._reset_everything()
        it = iter(css_str)
        while True:
            # Get current character.
            try:
                c = next(it)
            except StopIteration:
                break

            # Peek at next character (if possible).
            try:
                cn = next(it)
                it = itertools.chain([cn], it)
            except StopIteration:
                cn = None

            # Detect start of block or comment.
            if self.state == CssParserState.ROOT:
                if c in (" ", "\n"):
                    pass
                elif c == "/" and cn == "*":
                    self.state_change(CssParserState.ROOT_COMMENT)
                elif c == "{":
                    self.state_change(CssParserState.BLOCK)
                else:
                    self.state_change(CssParserState.SELECTOR)
                    self.css_selector_name_grow(c)

            # Handle root level comments.
            elif self.state == CssParserState.ROOT_COMMENT:
                if c == "*" and cn == "/":
                    next(it)  # Skip "/" as well.
                    self.state_change(CssParserState.ROOT)

            # Build the selector name.
            elif self.state == CssParserState.SELECTOR:
                if c in (" ", "\n"):
                    self.css_selector_finish()
                    self.state_change(CssParserState.ROOT)
                else:
                    self.css_selector_name_grow(c)

            # Detect start of property, comment, or end of block.
            elif self.state == CssParserState.BLOCK:
                if c in (" ", "\n"):
                    pass
                elif c == "/" and cn == "*":
                    self.state_change(CssParserState.BLOCK_COMMENT)
                elif c == "}":
                    self.css_rule_finish()
                    self.css_property_reset()
                    self.state_change(CssParserState.ROOT)
                else:
                    self.css_property_name_grow(c)
                    self.state_change(CssParserState.BLOCK_PROP_NAME)

            # Handle block level comments.
            elif self.state == CssParserState.BLOCK_COMMENT:
                if c == "*" and cn == "/":
                    next(it)  # Skip "/" as well.
                    self.state_change(CssParserState.BLOCK)

            # Build the property name and value.
            elif self.state == CssParserState.BLOCK_PROP_NAME:
                if c == ":":
                    self.state_change(CssParserState.BLOCK_GAP)
                else:
                    self.css_property_name_grow(c)
            elif self.state == CssParserState.BLOCK_GAP:
                if c in (" ", "\n"):
                    pass
                else:
                    self.css_property_value_grow(c)
                    self.state_change(CssParserState.BLOCK_PROP_VALUE)
            elif self.state == CssParserState.BLOCK_PROP_VALUE:
                if c == ";":
                    self.css_property_finish()
                    self.state_change(CssParserState.BLOCK)
                elif c == "}":
                    self.css_property_finish()
                    self.css_rule_finish()
                    self.state_change(CssParserState.ROOT)
                else:
                    self.css_property_value_grow(c)

        return self.new_sheet


class CssSheet(CssData):
    """Provides more advanced functionality for manipulating CSS data."""

    @classmethod
    def from_sheet(cls, sheet: "CssSheet", overwrite_values: str | None = None):
        """Create a new `CssSheet` from an existing `CssSheet`, optionally
        overwriting all values with `overwrite_values`.

        :param sheet: The `CssSheet` being copied.
        :param overwrite_values: If not `None`, replace all values with this
            value.
        :returns: A new `CssSheet`.
        """
        new_sheet = cls()
        new_sheet.rules = copy.deepcopy(sheet.rules)

        if overwrite_values is not None:
            for rule in new_sheet.rules:
                for prop in rule.properties:
                    prop.value = overwrite_values

        return new_sheet

    @staticmethod
    def selectors_name_combined(selectors: list[CssSelector]):
        """Combines a list of selectors into one string.

        :param selectors: The selectors to combine.
        :returns: The combined selector name.
        """
        return "-".join([s.name.lstrip(".") for s in selectors])

    @staticmethod
    def var_name(
        prefix: str, selectors_name: str, prop_name: str, in_var: bool = False
    ) -> str:
        """Combine a prefix, selector name and property name to generate a
        unique variable name.

        :param in_var: If `True`, wrap the variable name within "var()".
        :returns: The variable name.
        """
        ret = f"--{prefix}-{selectors_name}-{prop_name}"
        if in_var:
            return f"var({ret})"
        return ret

    def output_sheet(
        self,
        prefix: str | None = None,
        as_template: bool = False,
        template_values: list[str] | None = None,
    ) -> str:
        """Return the sheet as a CSS stylesheet.

        :param prefix: The prefix to use for all variable names. Must be
            supplied if `as_template` is enabled.
        :param as_template: Whether to substitute values with variable names.
        :param template_values: Which values to substitute with variable
            names. If `None`, all values are substituted. Requires
            `as_template` to be enabled.
        :returns: A string of the sheet as CSS, with variables substituted
            where specified.
        """

        if template_values is not None and prefix is None:
            raise ValueError("must supply a prefix")

        selectors_name: str

        def p2v(prop: CssProperty):
            """Helper function to return the correct value for printing the
            given property.
            """
            nonlocal as_template, prefix, selectors_name
            if as_template:
                if template_values is None:
                    return self.var_name(prefix, selectors_name, prop.name, in_var=True)
                if prop.value in template_values:
                    return self.var_name(prefix, selectors_name, prop.name, in_var=True)
                return prop.value
            return prop.value

        out: list[str] = []
        for rule in self.rules:
            selectors_name = self.selectors_name_combined(rule.selectors)
            out.append(" ".join(selector.name for selector in rule.selectors))
            out.append(" { ")
            out.append("; ".join(f"{p.name}: {p2v(p)}" for p in rule.properties))
            out.append(" }\n")
        return "".join(out)

    def output_vars(
        self, prefix: str | None = None, prefers_color_scheme: str | None = None
    ) -> str:
        """Return the sheet as CSS variables.

        :param prefix: The prefix to use for all variable names.
        :param prefers_color_scheme: The colour scheme which these variables
            target, which is used inside the `@media` block. Set to `None` for
            top-level, i.e. default variables.
        :returns: A string of all the CSS variables from the sheet, optionally
            wrapped inside a `@media` block as specified.
        """

        if prefix is None:
            raise ValueError("must supply a prefix")

        out: list[str] = []

        indent = "  "
        if prefers_color_scheme is None:
            out.append(":root {\n")
        else:
            out.append(f"@media (prefers-color-scheme: {prefers_color_scheme}) {{\n")
            out.append("  :root {\n")
            indent = "    "

        for rule in self.rules:
            selectors_name = self.selectors_name_combined(rule.selectors)
            for prop in rule.properties:
                _var_name = self.var_name(
                    prefix, selectors_name, prop.name, in_var=False
                )
                out.append(f"{indent}{_var_name}: {prop.value};\n")

        if prefers_color_scheme is None:
            out.append("}\n")
        else:
            out.append("  }\n")
            out.append("}\n")

        return "".join(out)

    def __and__(self, other):
        """Perform the intersection of two sheets. Returns a new sheet that
        only contains rules present in both sheets.

        >>> both = sheet_1 & sheet_2

        :param other: The instance to intersect with `self`.
        :returns: A new `CssSheet`.
        """
        if not isinstance(other, self.__class__):
            return NotImplemented

        new_sheet = CssSheet()

        for rule in self.rules:
            for prop in rule.properties:
                if other.has_property(selectors=rule.selectors, prop=prop):
                    new_sheet.append_property(selectors=rule.selectors, prop=prop)

        return new_sheet

    def __sub__(self, other):
        """Perform the subtraction of one sheet from another. Return a new
        new copy of self without any rules present in other.

        >>> sheet_1_only = sheet_1 - sheet_2

        :param other: The instance to subtract from `self`.
        :returns: A new `CssSheet`.
        """
        if not isinstance(other, self.__class__):
            return NotImplemented

        new_sheet = CssSheet()

        for rule in self.rules:
            for prop in rule.properties:
                if other.has_property(selectors=rule.selectors, prop=prop):
                    pass
                else:
                    new_sheet.append_property(selectors=rule.selectors, prop=prop)

        return new_sheet

    def _or_add(self, other, overwrite_with_other: bool):
        """Perform the addition of two sheets. Return a new sheet which
        contains rules from both `self` and `other`.

        :param other: The instance to or/add to `self`.
        :param overwrite_with_other: How to handle rules that exist in both
            sheets. If `True`, the `other` sheet takes precedence. If `False`,
            a `ValueError` is raised.
        :returns: A new `CssSheet`.
        :raises ValueError: If `overwrite_with_other` is `True` and a rule
            exists in both sheets.
        """
        if not isinstance(other, self.__class__):
            return NotImplemented

        new_sheet = CssSheet.from_sheet(other)

        for rule in self.rules:
            for prop in rule.properties:
                if new_sheet.has_property(
                    selectors=rule.selectors, prop=prop, compare_value=False
                ):
                    if overwrite_with_other:
                        pass
                    else:
                        raise ValueError(
                            "cannot add rule which exists in both sheets: "
                            f"selectors={rule.selectors}, property={prop}"
                        )
                else:
                    new_sheet.append_property(selectors=rule.selectors, prop=prop)

        return new_sheet

    def __or__(self, other):
        """Perform the addition of two sheets. Return a new sheet which
        contains rules from both `self` and `other`. If there are any

        >>> combined = sheet_1 | sheet_2

        :param other: The instance to or/add to `self`.
        :returns: A new `CssSheet`.
        :raises ValueError: If the same rule exists in both sheets.
        """
        return self._or_add(other, overwrite_with_other=False)

    def __add__(self, other):
        """Perform the addition of two sheets. Return a new sheet which
        contains rules from both `self` and `other`.

        >>> combined = sheet_1 + sheet_2

        :param other: The instance to or/add to `self`.
        :returns: A new `CssSheet`.
        """
        return self._or_add(other, overwrite_with_other=True)


def combine_themes(
    sheet_in_l: CssSheet, sheet_in_d: CssSheet
) -> tuple[CssSheet, CssSheet, CssSheet]:
    sheet_in_both = sheet_in_l & sheet_in_d

    sheet_unique_l = sheet_in_l - sheet_in_both
    sheet_unique_d = sheet_in_d - sheet_in_both

    sheet_unset_l = CssSheet.from_sheet(sheet_unique_l, overwrite_values="unset")
    sheet_unset_d = CssSheet.from_sheet(sheet_unique_d, overwrite_values="unset")

    sheet_unset_both = sheet_unset_l + sheet_unset_d

    sheet_vars_l = sheet_unset_both + sheet_unique_l
    sheet_vars_d = sheet_unset_both + sheet_unique_d

    combined = sheet_in_both | sheet_unset_both

    return (sheet_vars_l, sheet_vars_d, combined)



def main():
    """Generate a single theme from two themes, using CSS variables to enable
    switching between the two themes.

    Example usage:

    ```
    python process.py --css-light=github-light.scss --css-dark=github-dark.scss
    ```

    Will output `combined.css`.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--prefix", action="store", required=True, help="Prefix for CSS variables"
    )
    parser.add_argument(
        "--css-light", action="store", required=True, help="CSS file for light theme"
    )
    parser.add_argument(
        "--css-dark", action="store", required=True, help="CSS file for dark theme"
    )
    parser.add_argument(
        "--css-out", action="store", required=False, default="combined.css"
    )
    args = parser.parse_args()

    l_theme = CssSheet.from_file(filename=args.css_light)
    d_theme = CssSheet.from_file(filename=args.css_dark)

    vars_light, vars_dark, combined_theme = combine_themes(
        sheet_in_l=l_theme, sheet_in_d=d_theme
    )

    with open(args.css_out, "w") as handle:
        handle.write(vars_light.output_vars(prefix=args.prefix))
        handle.write(
            vars_dark.output_vars(prefix=args.prefix, prefers_color_scheme="dark")
        )
        handle.write(
            combined_theme.output_sheet(
                prefix=args.prefix, as_template=True, template_values=["unset"]
            )
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()


# Unit tests


def test_css_selectors_comparison():
    css_rule = CssRule(
        selectors=[CssSelector(name=".foo"), CssSelector(name=".bar")],
        properties=[
            CssProperty(name="color", value="red"),
            CssProperty(name="font-style", value="italic"),
        ],
    )

    assert css_rule.selectors == [CssSelector(name=".foo"), CssSelector(name=".bar")]
    assert css_rule.selectors != [CssSelector(name=".bar"), CssSelector(name=".foo")]
    assert css_rule.selectors != [CssSelector(name=".foo")]
    assert css_rule.selectors != [CssSelector(name=".bar")]
    assert css_rule.selectors != [
        CssSelector(name=".foo"),
        CssSelector(name=".bar"),
        CssSelector(name=".baz"),
    ]


def test_css_selectors_combine():
    selectors = [
        CssSelector(name=".foo"),
        CssSelector(name=".bar"),
        CssSelector(name=".baz"),
    ]
    selectors_name = CssSheet.selectors_name_combined(selectors)
    assert selectors_name == "foo-bar-baz"


def test_css_sheet_has_property():
    css_sheet: CssSheet = CssSheet(
        rules=[
            CssRule(
                selectors=[CssSelector(name=".a"), CssSelector(name=".b")],
                properties=[
                    CssProperty(name="color", value="#FF00FF"),
                    CssProperty(name="background-color", value="#FF0000"),
                ],
            ),
            CssRule(
                selectors=[CssSelector(name=".a"), CssSelector(name=".c")],
                properties=[
                    CssProperty(name="color", value="#0000FF"),
                    CssProperty(name="background-color", value="#00FF00"),
                ],
            ),
            CssRule(
                selectors=[CssSelector(name=".d"), CssSelector(name=".c")],
                properties=[
                    CssProperty(name="color", value="#FFFF00"),
                    CssProperty(name="background-color", value="#00FFFF"),
                ],
            ),
        ]
    )

    # Verify data contains property with given value that matches.
    assert (
        css_sheet.has_property(
            selectors=[CssSelector(name=".a"), CssSelector(name=".b")],
            prop=CssProperty(name="color", value="#FF00FF"),
            compare_value=True,
        )
        is True
    )

    # Verify data does not contain property with given value that does not match.
    assert (
        css_sheet.has_property(
            selectors=[CssSelector(name=".a"), CssSelector(name=".b")],
            prop=CssProperty(name="color", value="#ABCDEF"),
            compare_value=True,
        )
        is False
    )

    # Verify data does contain property with given value that does not match,
    # but is ignored.
    assert (
        css_sheet.has_property(
            selectors=[CssSelector(name=".a"), CssSelector(name=".b")],
            prop=CssProperty(name="color", value="#ABCDEF"),
            compare_value=False,
        )
        is True
    )


EXAMPLE_CSS_1 = """\
/* Root level comment */
body {
    color: #2A2A2A;
    /* Block level comment */
    font-size: 17px;
    line-height: 26px;
}

/* Another root level comment */
h1 {
    color: #473247; /* Inline block level comment */
    font-size: 40px;
    line-height: 48px;
}

.my-class .another-class {
    color: red;
    padding: 0 0.4em 0 0.4em;
}
"""


def test_css_parser():
    logging.basicConfig(level=logging.DEBUG)
    css_parser = CssParser()
    css_sheet: CssSheet = css_parser.parse(EXAMPLE_CSS_1)
    assert (
        CssRule(
            selectors=[CssSelector(name="body")],
            properties=[
                CssProperty(name="color", value="#2A2A2A"),
                CssProperty(name="font-size", value="17px"),
                CssProperty(name="line-height", value="26px"),
            ],
        )
        in css_sheet.rules
    )
    assert (
        CssRule(
            selectors=[CssSelector(name="h1")],
            properties=[
                CssProperty(name="color", value="#473247"),
                CssProperty(name="font-size", value="40px"),
                CssProperty(name="line-height", value="48px"),
            ],
        )
        in css_sheet.rules
    )
    assert (
        CssRule(
            selectors=[
                CssSelector(name=".my-class"),
                CssSelector(name=".another-class"),
            ],
            properties=[
                CssProperty(name="color", value="red"),
                CssProperty(name="padding", value="0 0.4em 0 0.4em"),
            ],
        )
        in css_sheet.rules
    )


# Portions of the "github" and "github-dark" themes, selected to ensure
# examples of all fields as defined in `ClassData` are available.
EXAMPLE_LIGHT_THEME_IN = """\
/* Background */ .bg { background-color: #ffffff; }
/* PreWrapper */ .chroma { background-color: #ffffff; }
/* Other */ .chroma .x {  }
/* Error */ .chroma .err { color: #a61717; background-color: #e3d2d2 }
/* CodeLine */ .chroma .cl {  }
/* LineLink */ .chroma .lnlinks { outline: none; text-decoration: none; color: inherit }
/* LineTableTD */ .chroma .lntd { vertical-align: top; padding: 0; margin: 0; border: 0; }
/* LineTable */ .chroma .lntable { border-spacing: 0; padding: 0; margin: 0; border: 0; }
/* LineHighlight */ .chroma .hl { background-color: #ffffcc }
/* LineNumbersTable */ .chroma .lnt { white-space: pre; -webkit-user-select: none; user-select: none; margin-right: 0.4em; padding: 0 0.4em 0 0.4em;color: #7f7f7f }
/* LineNumbers */ .chroma .ln { white-space: pre; -webkit-user-select: none; user-select: none; margin-right: 0.4em; padding: 0 0.4em 0 0.4em;color: #7f7f7f }
/* Line */ .chroma .line { display: flex; }
/* Keyword */ .chroma .k { color: #000000; font-weight: bold }
/* KeywordConstant */ .chroma .kc { color: #000000; font-weight: bold }
/* Comment */ .chroma .c { color: #999988; font-style: italic }
"""
EXAMPLE_LIGHT_THEME_OUT = """\
.bg { background-color: #ffffff }
.chroma { background-color: #ffffff }
.chroma .x {  }
.chroma .err { color: #a61717; background-color: #e3d2d2 }
.chroma .cl {  }
.chroma .lnlinks { outline: none; text-decoration: none; color: inherit }
.chroma .lntd { vertical-align: top; padding: 0; margin: 0; border: 0 }
.chroma .lntable { border-spacing: 0; padding: 0; margin: 0; border: 0 }
.chroma .hl { background-color: #ffffcc }
.chroma .lnt { white-space: pre; -webkit-user-select: none; user-select: none; margin-right: 0.4em; padding: 0 0.4em 0 0.4em; color: #7f7f7f }
.chroma .ln { white-space: pre; -webkit-user-select: none; user-select: none; margin-right: 0.4em; padding: 0 0.4em 0 0.4em; color: #7f7f7f }
.chroma .line { display: flex }
.chroma .k { color: #000000; font-weight: bold }
.chroma .kc { color: #000000; font-weight: bold }
.chroma .c { color: #999988; font-style: italic }
"""
EXAMPLE_LIGHT_THEME_TEMPLATE = """\
.bg { background-color: var(--xyzzy-bg-background-color) }
.chroma { background-color: var(--xyzzy-chroma-background-color) }
.chroma .x {  }
.chroma .err { color: var(--xyzzy-chroma-err-color); background-color: var(--xyzzy-chroma-err-background-color) }
.chroma .cl {  }
.chroma .lnlinks { outline: var(--xyzzy-chroma-lnlinks-outline); text-decoration: var(--xyzzy-chroma-lnlinks-text-decoration); color: var(--xyzzy-chroma-lnlinks-color) }
.chroma .lntd { vertical-align: var(--xyzzy-chroma-lntd-vertical-align); padding: var(--xyzzy-chroma-lntd-padding); margin: var(--xyzzy-chroma-lntd-margin); border: var(--xyzzy-chroma-lntd-border) }
.chroma .lntable { border-spacing: var(--xyzzy-chroma-lntable-border-spacing); padding: var(--xyzzy-chroma-lntable-padding); margin: var(--xyzzy-chroma-lntable-margin); border: var(--xyzzy-chroma-lntable-border) }
.chroma .hl { background-color: var(--xyzzy-chroma-hl-background-color) }
.chroma .lnt { white-space: var(--xyzzy-chroma-lnt-white-space); -webkit-user-select: var(--xyzzy-chroma-lnt--webkit-user-select); user-select: var(--xyzzy-chroma-lnt-user-select); margin-right: var(--xyzzy-chroma-lnt-margin-right); padding: var(--xyzzy-chroma-lnt-padding); color: var(--xyzzy-chroma-lnt-color) }
.chroma .ln { white-space: var(--xyzzy-chroma-ln-white-space); -webkit-user-select: var(--xyzzy-chroma-ln--webkit-user-select); user-select: var(--xyzzy-chroma-ln-user-select); margin-right: var(--xyzzy-chroma-ln-margin-right); padding: var(--xyzzy-chroma-ln-padding); color: var(--xyzzy-chroma-ln-color) }
.chroma .line { display: var(--xyzzy-chroma-line-display) }
.chroma .k { color: var(--xyzzy-chroma-k-color); font-weight: var(--xyzzy-chroma-k-font-weight) }
.chroma .kc { color: var(--xyzzy-chroma-kc-color); font-weight: var(--xyzzy-chroma-kc-font-weight) }
.chroma .c { color: var(--xyzzy-chroma-c-color); font-style: var(--xyzzy-chroma-c-font-style) }
"""


def test_parse_light_theme():
    css_sheet = CssSheet.from_str(EXAMPLE_LIGHT_THEME_IN)
    assert css_sheet.output_sheet() == EXAMPLE_LIGHT_THEME_OUT


def test_template_light_theme():
    css_sheet = CssSheet.from_str(EXAMPLE_LIGHT_THEME_IN)
    assert (
        css_sheet.output_sheet(prefix="xyzzy", as_template=True)
        == EXAMPLE_LIGHT_THEME_TEMPLATE
    )


EXAMPLE_DARK_THEME_IN = """\
/* Background */ .bg { color: #c9d1d9; background-color: #0d1117; }
/* PreWrapper */ .chroma { color: #c9d1d9; background-color: #0d1117; }
/* Other */ .chroma .x {  }
/* Error */ .chroma .err { color: #f85149 }
/* CodeLine */ .chroma .cl {  }
/* LineLink */ .chroma .lnlinks { outline: none; text-decoration: none; color: inherit }
/* LineTableTD */ .chroma .lntd { vertical-align: top; padding: 0; margin: 0; border: 0; }
/* LineTable */ .chroma .lntable { border-spacing: 0; padding: 0; margin: 0; border: 0; }
/* LineHighlight */ .chroma .hl { background-color: #ffffcc }
/* LineNumbersTable */ .chroma .lnt { white-space: pre; -webkit-user-select: none; user-select: none; margin-right: 0.4em; padding: 0 0.4em 0 0.4em;color: #64686c }
/* LineNumbers */ .chroma .ln { white-space: pre; -webkit-user-select: none; user-select: none; margin-right: 0.4em; padding: 0 0.4em 0 0.4em;color: #6e7681 }
/* Line */ .chroma .line { display: flex; }
/* Keyword */ .chroma .k { color: #ff7b72 }
/* KeywordConstant */ .chroma .kc { color: #79c0ff }
/* Comment */ .chroma .c { color: #8b949e; font-style: italic }
"""
EXAMPLE_DARK_THEME_OUT = """\
.bg { color: #c9d1d9; background-color: #0d1117 }
.chroma { color: #c9d1d9; background-color: #0d1117 }
.chroma .x {  }
.chroma .err { color: #f85149 }
.chroma .cl {  }
.chroma .lnlinks { outline: none; text-decoration: none; color: inherit }
.chroma .lntd { vertical-align: top; padding: 0; margin: 0; border: 0 }
.chroma .lntable { border-spacing: 0; padding: 0; margin: 0; border: 0 }
.chroma .hl { background-color: #ffffcc }
.chroma .lnt { white-space: pre; -webkit-user-select: none; user-select: none; margin-right: 0.4em; padding: 0 0.4em 0 0.4em; color: #64686c }
.chroma .ln { white-space: pre; -webkit-user-select: none; user-select: none; margin-right: 0.4em; padding: 0 0.4em 0 0.4em; color: #6e7681 }
.chroma .line { display: flex }
.chroma .k { color: #ff7b72 }
.chroma .kc { color: #79c0ff }
.chroma .c { color: #8b949e; font-style: italic }
"""
EXAMPLE_DARK_THEME_TEMPLATE = """\
.bg { color: var(--xyzzy-bg-color); background-color: var(--xyzzy-bg-background-color) }
.chroma { color: var(--xyzzy-chroma-color); background-color: var(--xyzzy-chroma-background-color) }
.chroma .x {  }
.chroma .err { color: var(--xyzzy-chroma-err-color) }
.chroma .cl {  }
.chroma .lnlinks { outline: var(--xyzzy-chroma-lnlinks-outline); text-decoration: var(--xyzzy-chroma-lnlinks-text-decoration); color: var(--xyzzy-chroma-lnlinks-color) }
.chroma .lntd { vertical-align: var(--xyzzy-chroma-lntd-vertical-align); padding: var(--xyzzy-chroma-lntd-padding); margin: var(--xyzzy-chroma-lntd-margin); border: var(--xyzzy-chroma-lntd-border) }
.chroma .lntable { border-spacing: var(--xyzzy-chroma-lntable-border-spacing); padding: var(--xyzzy-chroma-lntable-padding); margin: var(--xyzzy-chroma-lntable-margin); border: var(--xyzzy-chroma-lntable-border) }
.chroma .hl { background-color: var(--xyzzy-chroma-hl-background-color) }
.chroma .lnt { white-space: var(--xyzzy-chroma-lnt-white-space); -webkit-user-select: var(--xyzzy-chroma-lnt--webkit-user-select); user-select: var(--xyzzy-chroma-lnt-user-select); margin-right: var(--xyzzy-chroma-lnt-margin-right); padding: var(--xyzzy-chroma-lnt-padding); color: var(--xyzzy-chroma-lnt-color) }
.chroma .ln { white-space: var(--xyzzy-chroma-ln-white-space); -webkit-user-select: var(--xyzzy-chroma-ln--webkit-user-select); user-select: var(--xyzzy-chroma-ln-user-select); margin-right: var(--xyzzy-chroma-ln-margin-right); padding: var(--xyzzy-chroma-ln-padding); color: var(--xyzzy-chroma-ln-color) }
.chroma .line { display: var(--xyzzy-chroma-line-display) }
.chroma .k { color: var(--xyzzy-chroma-k-color) }
.chroma .kc { color: var(--xyzzy-chroma-kc-color) }
.chroma .c { color: var(--xyzzy-chroma-c-color); font-style: var(--xyzzy-chroma-c-font-style) }
"""


def test_parse_dark_theme():
    css_sheet = CssSheet.from_str(EXAMPLE_DARK_THEME_IN)
    assert css_sheet.output_sheet() == EXAMPLE_DARK_THEME_OUT


def test_template_dark_theme():
    css_sheet = CssSheet.from_str(EXAMPLE_DARK_THEME_IN)
    assert (
        css_sheet.output_sheet(prefix="xyzzy", as_template=True)
        == EXAMPLE_DARK_THEME_TEMPLATE
    )


EXAMPLE_OUTPUT_COMBINED = """\
:root {
  --widget-bg-background-color: #ffffff;
  --widget-bg-color: unset;
  --widget-chroma-background-color: #ffffff;
  --widget-chroma-color: unset;
  --widget-chroma-err-color: #a61717;
  --widget-chroma-err-background-color: #e3d2d2;
  --widget-chroma-lnt-color: #7f7f7f;
  --widget-chroma-ln-color: #7f7f7f;
  --widget-chroma-k-color: #000000;
  --widget-chroma-k-font-weight: bold;
  --widget-chroma-kc-color: #000000;
  --widget-chroma-kc-font-weight: bold;
  --widget-chroma-c-color: #999988;
}
@media (prefers-color-scheme: dark) {
  :root {
    --widget-bg-color: #c9d1d9;
    --widget-bg-background-color: #0d1117;
    --widget-chroma-color: #c9d1d9;
    --widget-chroma-background-color: #0d1117;
    --widget-chroma-err-color: #f85149;
    --widget-chroma-err-background-color: unset;
    --widget-chroma-lnt-color: #64686c;
    --widget-chroma-ln-color: #6e7681;
    --widget-chroma-k-color: #ff7b72;
    --widget-chroma-k-font-weight: unset;
    --widget-chroma-kc-color: #79c0ff;
    --widget-chroma-kc-font-weight: unset;
    --widget-chroma-c-color: #8b949e;
  }
}
.bg { color: var(--widget-bg-color); background-color: var(--widget-bg-background-color) }
.chroma { color: var(--widget-chroma-color); background-color: var(--widget-chroma-background-color) }
.chroma .err { color: var(--widget-chroma-err-color); background-color: var(--widget-chroma-err-background-color) }
.chroma .lnt { color: var(--widget-chroma-lnt-color); white-space: pre; -webkit-user-select: none; user-select: none; margin-right: 0.4em; padding: 0 0.4em 0 0.4em }
.chroma .ln { color: var(--widget-chroma-ln-color); white-space: pre; -webkit-user-select: none; user-select: none; margin-right: 0.4em; padding: 0 0.4em 0 0.4em }
.chroma .k { color: var(--widget-chroma-k-color); font-weight: var(--widget-chroma-k-font-weight) }
.chroma .kc { color: var(--widget-chroma-kc-color); font-weight: var(--widget-chroma-kc-font-weight) }
.chroma .c { color: var(--widget-chroma-c-color); font-style: italic }
.chroma .lnlinks { outline: none; text-decoration: none; color: inherit }
.chroma .lntd { vertical-align: top; padding: 0; margin: 0; border: 0 }
.chroma .lntable { border-spacing: 0; padding: 0; margin: 0; border: 0 }
.chroma .hl { background-color: #ffffcc }
.chroma .line { display: flex }
"""


def test_main():
    sheet_in_l = CssSheet.from_str(EXAMPLE_LIGHT_THEME_IN)
    sheet_in_d = CssSheet.from_str(EXAMPLE_DARK_THEME_IN)

    vars_light, vars_dark, combined_theme = combine_themes(sheet_in_l, sheet_in_d)

    out_sections = []
    out_sections.append(vars_light.output_vars(prefix="widget"))
    out_sections.append(
        vars_dark.output_vars(prefix="widget", prefers_color_scheme="dark")
    )
    out_sections.append(
        combined_theme.output_sheet(
            prefix="widget", as_template=True, template_values=["unset"]
        )
    )

    out_combined = "".join(out_sections)

    assert out_combined == EXAMPLE_OUTPUT_COMBINED
