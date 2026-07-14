import kipy

def find_courtyard_structure():
    kicad = kipy.KiCad()
    board = kicad.get_board()
    fps = board.get_footprints()
    
    if not fps:
        print("Плата пуста!")
        return
        
    fp = fps[0]
    try:
        ref = fp.reference_field.text.value
    except:
        ref = "Unknown"
        
    print(f"=== Анализируем компонент: {ref} ===\n")
    
    # 1. Ищем прямые свойства (не методы)
    keywords = ['courtyard', 'shape', 'polygon', 'graphic', 'drawing', 'rect']
    print("--- Ищем свойства, связанные с формами/контуром ---")
    for attr in dir(fp):
        if any(kw in attr.lower() for kw in keywords):
            val = getattr(fp, attr)
            if not callable(val):
                val_str = str(val)
                # Отсекаем слишком длинные списки для читаемости
                if len(val_str) > 300:
                    val_str = val_str[:300] + f"... [длина строки: {len(str(val))}]"
                print(f"  {attr:<25} | Тип: {type(val).__name__:<15} | {val_str}")
                
    # 2. Ищем методы
    print("\n--- Ищем МЕТОДЫ для получения форм ---")
    for attr in dir(fp):
        if any(kw in attr.lower() for kw in keywords):
            val = getattr(fp, attr)
            if callable(val):
                print(f"  {attr:<25} | (Вызываемый метод)")
                
    # 3. Самое важное: ищем в сыром proto
    print("\n--- Анализ сырого proto (ищем CrtYd, courtyard, polygon) ---")
    if hasattr(fp, 'proto'):
        proto_str = str(fp.proto)
        
        # KiCad обычно называет слой контура F.CrtYd или B.CrtYd
        search_terms = ['CrtYd', 'courtyard', 'polygon']
        found = False
        
        for term in search_terms:
            idx = proto_str.find(term)
            if idx != -1:
                found = True
                print(f"\nНайдено '{term}'! Фрагмент proto:")
                # Выводим кусокproto вокруг найденного слова
                start = max(0, idx - 50)
                end = min(len(proto_str), idx + 500)
                print(proto_str[start:end])
                print("...")
                break # Если нашли CrtYd, остальные смотреть не обязательно
                
        if not found:
            print("В proto НЕТ упоминаний CrtYd/courtyard/polygon.")
            print("(Возможно, у этого компонента просто не нарисован courtyard, попробуйте выделить другой, например IC401)")
    else:
        print("Атрибута proto нет!")

if __name__ == "__main__":
    find_courtyard_structure()