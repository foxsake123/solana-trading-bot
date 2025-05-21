file_path = 'core/trading_bot.py'

with open(file_path, 'r') as file:
    lines = file.readlines()

fixed_lines = []
in_docstring = False
docstring_start_line = 0

for i, line in enumerate(lines):
    # Check for docstring start
    if '"""' in line and not in_docstring:
        in_docstring = True
        docstring_start_line = i
        # Count quotes in this line
        if line.count('"""') == 2:
            # Docstring starts and ends on same line
            in_docstring = False
    
    # Check for docstring end
    elif '"""' in line and in_docstring:
        in_docstring = False
    
    fixed_lines.append(line)

# If we're still in a docstring at the end, fix it
if in_docstring:
    print(f"Found unterminated docstring starting at line {docstring_start_line + 1}")
    # Add closing quotes to the last line of the docstring
    docstring_line = lines[docstring_start_line]
    
    # Find where in the line the opening quotes are
    start_pos = docstring_line.find('"""')
    indentation = docstring_line[:start_pos]
    
    # Add a line with closing quotes
    fixed_lines.append(f"{indentation}"""\n")
    print(f"Added closing quotes after line {len(lines)}")

# Write the fixed file
with open(file_path, 'w') as file:
    file.writelines(fixed_lines)

print(f"Fixed docstring in {file_path}")