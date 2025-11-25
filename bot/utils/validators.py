"""
Валидаторы данных
"""
import re


class Validators:
    """Валидаторы входных данных"""
    
    @staticmethod
    def is_valid_phone(phone: str) -> bool:
        """
        Проверка корректности номера телефона
        Формат: +7XXXXXXXXXX или 8XXXXXXXXXX
        """
        # Удаляем пробелы, тире, скобки
        clean_phone = re.sub(r'[\s\-\(\)]', '', phone)
        
        # Проверяем формат
        pattern = r'^(\+7|8)\d{10}$'
        return bool(re.match(pattern, clean_phone))
    
    @staticmethod
    def normalize_phone(phone: str) -> str:
        """Нормализация номера телефона к формату +7XXXXXXXXXX"""
        clean_phone = re.sub(r'[\s\-\(\)]', '', phone)
        
        if clean_phone.startswith('8'):
            clean_phone = '+7' + clean_phone[1:]
        elif not clean_phone.startswith('+'):
            clean_phone = '+' + clean_phone
        
        return clean_phone
    
    @staticmethod
    def is_valid_car_number(car_number: str) -> bool:
        """
        Проверка корректности номера автомобиля
        Формат: А123БВ123 или A123BC123
        """
        # Русские номера
        pattern_ru = r'^[АВЕКМНОРСТУХ]\d{3}[АВЕКМНОРСТУХ]{2}\d{2,3}$'
        # Латинские номера
        pattern_en = r'^[ABEKMHOPCTYX]\d{3}[ABEKMHOPCTYX]{2}\d{2,3}$'
        
        clean_number = car_number.upper().replace(' ', '')
        
        return bool(re.match(pattern_ru, clean_number) or re.match(pattern_en, clean_number))
    
    @staticmethod
    def is_valid_coordinates(lat: float, lon: float) -> bool:
        """Проверка корректности координат"""
        return -90 <= lat <= 90 and -180 <= lon <= 180
    
    @staticmethod
    def is_valid_rating(rating: int) -> bool:
        """Проверка корректности оценки"""
        return 1 <= rating <= 5

