seqr developer guide
====================

Software contributer code style

To allow multiple developers to contribute to the code-base and function simultaneously and effectively, please utilize the following style guide. We were inspired by the Google Python comment styling.

1. Tabs must be 4 character length

2. All comments function and method comments must be doc tags. For example,

```
def functionA()
	"""
	Comment
	"""
	pass
```

3. Comment must start with uppercase character


4. Args must be described in the comments


```
def functionA(arg1, arg2)
	"""
	First line: High level description in a single line
	<space>
	Args:
		arg1: <description>
		arg2: <description>
	<space>
	Returns:
		<high level description>
		<space>
		<brief example of data structure>
	<space>
	Raises:
		<description>
	"""
	pass
```