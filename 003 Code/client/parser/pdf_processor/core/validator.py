def is_valid_table(table_data) -> bool:
    if not table_data or len(table_data) < 2:
        return False

    col_counts = [len([cell for cell in row if (str(cell).strip() if cell else "").strip() != ""]) for row in table_data]
    if max(col_counts, default=0) < 2:
        return False

    empty_rows = sum(1 for row in table_data if all((str(cell).strip() if cell else "") == "" for cell in row))
    if empty_rows / len(table_data) > 0.5:
        return False

    return True