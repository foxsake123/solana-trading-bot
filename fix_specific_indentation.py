import os

def fix_specific_indentation(filename):
    print(f"Fixing specific indentation issue in: {filename}")
    
    with open(filename, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    # Create backup
    backup_file = filename + '.specific.bak'
    with open(backup_file, 'w', encoding='utf-8') as file:
        file.writelines(lines)
    print(f"Created backup at: {backup_file}")
    
    # Find the problematic line (line 1685)
    target_line_number = 1685
    problem_area_start = max(0, target_line_number - 20)
    problem_area_end = min(len(lines), target_line_number + 20)
    
    print(f"Analyzing lines {problem_area_start} to {problem_area_end}")
    
    # Print the problematic section for diagnosis
    for i in range(problem_area_start, problem_area_end):
        line_num = i + 1  # 1-based line numbering
        indent_count = len(lines[i]) - len(lines[i].lstrip())
        if line_num == target_line_number:
            print(f"Line {line_num} (TARGET, indent={indent_count}): {lines[i].rstrip()}")
        else:
            print(f"Line {line_num} (indent={indent_count}): {lines[i].rstrip()}")
    
    # Fix the indentation of the problematic section
    # Look for the 'if completed_trades:' line, and ensure all code inside has consistent indentation
    in_block = False
    expected_indent = None
    for i in range(problem_area_start, problem_area_end):
        line = lines[i]
        stripped = line.strip()
        
        # Looking for the start of the block
        if "if completed_trades:" in line:
            in_block = True
            expected_indent = len(line) - len(line.lstrip()) + 4  # Base indent + 4 spaces
            print(f"Found block start at line {i+1}, expected indent: {expected_indent}")
        
        # If we're in the block with the issue
        if in_block and target_line_number-1 <= i <= target_line_number+1:
            current_indent = len(line) - len(line.lstrip())
            if current_indent != expected_indent and stripped:  # If not blank line
                fixed_line = ' ' * expected_indent + stripped + '\n'
                print(f"Fixing line {i+1}: {current_indent} -> {expected_indent}")
                lines[i] = fixed_line
    
    # Write fixed content
    with open(filename, 'w', encoding='utf-8') as file:
        file.writelines(lines)
    print(f"Fixed specific indentation issues in: {filename}")
    return True

# Fix the file in the core directory
fix_specific_indentation('core/enhanced_dashboard.py')