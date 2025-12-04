#!/usr/bin/env python3
"""
Создать файл accounts.txt из списка номеров
"""

import sys

def create_accounts_file(numbers: list, filename: str = 'accounts.txt'):
    """Создать файл с номерами"""
    with open(filename, 'w', encoding='utf-8') as f:
        for number in numbers:
            f.write(f"{number}\n")
    
    print(f"✅ Создан файл {filename} с {len(numbers)} номерами")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python create-accounts-file.py +79001234567 +79001234568 ...")
        print("\nИли создайте файл accounts.txt вручную:")
        print("  +79001234567")
        print("  +79001234568")
        print("  +79001234569")
        sys.exit(1)
    
    numbers = sys.argv[1:]
    create_accounts_file(numbers)
    print(f"\nТеперь запустите:")
    print(f"  python scripts/batch-get-sessions.py accounts.txt")

