from django.db import models


class Bank(models.Model):
    name = models.CharField(max_length=50, default="Не указано")

    def __str__(self):
        return self.name

    class Meta:
        managed = False
        db_table = 'bank'
        verbose_name = 'Банк'
        verbose_name_plural = 'Банки'

class City(models.Model):
    city_name = models.CharField(max_length=25, default="Не указано")

    def __str__(self):
        return self.city_name

    class Meta:
        managed = False
        db_table = 'city'
        verbose_name = 'Город'
        verbose_name_plural = 'Города'

class Classification(models.Model):
    name = models.CharField(max_length=25, default="Не указано")

    def __str__(self):
        return self.name

    class Meta:
        managed = False
        db_table = 'classification'
        verbose_name = 'Классификация'
        verbose_name_plural = 'Классификации'


class Client(models.Model):
    name = models.CharField(max_length=25, default="Не указано")

    def __str__(self):
        return self.name

    class Meta:
        managed = False
        db_table = 'client'
        verbose_name = 'Клиент'
        verbose_name_plural = 'Клиенты'


class ConstructionManagement(models.Model):
    name = models.CharField(max_length=25, default="Не указано")

    def __str__(self):
        return self.name

    class Meta:
        managed = False
        db_table = 'construction_management'
        verbose_name = 'Строительное управление'
        verbose_name_plural = 'Строительные управления'


class ConstructionSite(models.Model):
    contract = models.ForeignKey('Contract', models.DO_NOTHING)
    object_kind = models.ForeignKey('ObjectKind', models.DO_NOTHING)
    city = models.ForeignKey(City, models.DO_NOTHING, blank=True, null=True)
    street = models.ForeignKey('Street', models.DO_NOTHING, blank=True, null=True)
    region = models.ForeignKey('Region', models.DO_NOTHING, blank=True, null=True)
    name = models.CharField(max_length=25, default="Не указано")
    house_number = models.CharField(max_length=10, blank=True, null=True, default="")

    def __str__(self):
        return self.name

    class Meta:
        managed = False
        db_table = 'construction_site'
        verbose_name = 'Строительный объект'
        verbose_name_plural = 'Строительные объекты'


class Contract(models.Model):
    construction_management = models.ForeignKey(ConstructionManagement, models.DO_NOTHING)
    client = models.ForeignKey(Client, models.DO_NOTHING)
    contract_number = models.CharField(max_length=25, default="Не указано")

    def __str__(self):
        return self.contract_number

    class Meta:
        managed = False
        db_table = 'contract'
        verbose_name = 'Договор'
        verbose_name_plural = 'Договора'


class Crew(models.Model):
    leader_employee = models.ForeignKey('Employee', models.DO_NOTHING, blank=True, null=True)
    name = models.CharField(max_length=25, default="Не указано")

    def __str__(self):
        return self.name

    class Meta:
        managed = False
        db_table = 'crew'
        verbose_name = 'Бригада'
        verbose_name_plural = 'Бригады'


class CrewComposition(models.Model):
    crew = models.ForeignKey(Crew, models.DO_NOTHING)
    employee = models.ForeignKey('Employee', models.DO_NOTHING)

    def __str__(self):
        return f"{self.employee} в бригаде {self.crew}"

    class Meta:
        managed = False
        db_table = 'crew_composition'
        unique_together = (('crew', 'employee'),)
        verbose_name = 'Состав бригад'
        verbose_name_plural = 'Составы бригад'

class CrewGroup(models.Model):
    construction_site = models.ForeignKey(ConstructionSite, models.DO_NOTHING)
    crew = models.ForeignKey(Crew, models.DO_NOTHING)

    def __str__(self):
        return f"Бригада {self.crew} на объекте {self.construction_site}"

    class Meta:
        managed = False
        db_table = 'crew_group'
        unique_together = (('construction_site', 'crew'),)
        verbose_name = 'Группа бригад'
        verbose_name_plural = 'Группы бригад'

class Department(models.Model):
    name = models.CharField(max_length=25, default="Не указано")

    def __str__(self):
        return self.name

    class Meta:
        managed = False
        db_table = 'department'
        verbose_name = 'Структурное подразделение'
        verbose_name_plural = 'Структурные подразделения'

class Employee(models.Model):
    GENDER_CHOICES = [
        ('Мужской', 'Мужской'),
        ('Женский', 'Женский'),
    ]
    city = models.ForeignKey(City, models.DO_NOTHING, blank=True, null=True)
    street = models.ForeignKey('Street', models.DO_NOTHING, blank=True, null=True)
    region = models.ForeignKey('Region', models.DO_NOTHING, blank=True, null=True)
    first_name = models.CharField(max_length=25, default="Не указано")
    middle_name = models.CharField(max_length=25, blank=True, null=True, default="")
    last_name = models.CharField(max_length=25, default="Не указано")
    birth_date = models.DateField(default="2000-01-01")
    house_number = models.CharField(max_length=10, blank=True, null=True, default="")
    work_experience = models.FloatField(blank=True, null=True, default=0.0)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True, default="Мужской")

    def __str__(self):
        full_name_parts = [self.last_name, self.first_name]
        if self.middle_name:
            full_name_parts.append(self.middle_name)
        return " ".join(full_name_parts)

    class Meta:
        managed = False
        db_table = 'employee'
        verbose_name = 'Работник'
        verbose_name_plural = 'Работники'

class EmploymentRecord(models.Model):
    EVENT_TYPE_CHOICES = [
        ('Приём', 'Приём'),
        ('Перевод', 'Перевод'),
        ('Увольнение', 'Увольнение'),
    ]

    employee = models.ForeignKey(Employee, models.DO_NOTHING)
    department = models.ForeignKey(Department, models.DO_NOTHING, blank=True, null=True)
    workplace = models.ForeignKey('Workplace', models.DO_NOTHING, blank=True, null=True)
    profession = models.ForeignKey('Profession', models.DO_NOTHING, blank=True, null=True)
    specialty = models.ForeignKey('Specialty', models.DO_NOTHING, blank=True, null=True)
    classification = models.ForeignKey(Classification, models.DO_NOTHING, blank=True, null=True)
    hire_date = models.DateField(default="01.01.2000")
    termination_date = models.DateField(blank=True, null=True, default=None)
    event_position = models.ForeignKey('Position', models.DO_NOTHING, blank=True, null=True)
    employment_status = models.CharField(max_length=10, blank=True, null=True, default="")
    event_type = models.CharField(max_length=10, choices=EVENT_TYPE_CHOICES, blank=True, null=True, default="Приём")
    termination_reason = models.CharField(max_length=100, blank=True, null=True, default="")

    def __str__(self):
        return f"Запись о работе {self.employee} с {self.hire_date}"

    class Meta:
        managed = False
        db_table = 'employment_record'
        verbose_name = 'Трудовая книжка'
        verbose_name_plural = 'Трудовые книжки'

class Equipment(models.Model):
    EQUIPMENT_TYPE_CHOICES = [
        ('Экскаватор', 'Экскаватор'),
        ('Бульдозер', 'Бульдозер'),
        ('Подъемный кран', 'Подъемный кран'),
        ('Ковш', 'Ковш'),
        ('Самосвал', 'Самосвал'),
        ('Бетономешалка', 'Бетономешалка'),
        ('Погрузчик', 'Погрузчик'),
        ('Трактор', 'Трактор'),
        ('Другое', 'Другое'),
    ]

    equipment_name = models.CharField(max_length=150, default="Не указано")
    equipment_type = models.CharField(max_length=20, choices=EQUIPMENT_TYPE_CHOICES, blank=True, null=True, default="Другое")

    def __str__(self):
        return self.equipment_name

    class Meta:
        managed = False
        db_table = 'equipment'
        verbose_name = 'Строительная техника'
        verbose_name_plural = 'Строительная техника'

class EquipmentAtSite(models.Model):
    construction_site = models.ForeignKey(ConstructionSite, models.DO_NOTHING)
    equipment = models.ForeignKey(Equipment, models.DO_NOTHING)

    def __str__(self):
        return f"{self.equipment} на объекте {self.construction_site}"

    class Meta:
        managed = False
        db_table = 'equipment_at_site'
        unique_together = (('construction_site', 'equipment'),)
        verbose_name = 'Строительная техника на объекте'
        verbose_name_plural = 'Строительная техника на объектах'

class EquipmentManagement(models.Model):
    construction_management = models.ForeignKey(ConstructionManagement, models.DO_NOTHING)
    equipment = models.ForeignKey(Equipment, models.DO_NOTHING)

    def __str__(self):
        return f"{self.equipment} в управлении {self.construction_management}"

    class Meta:
        managed = False
        db_table = 'equipment_management'
        unique_together = (('construction_management', 'equipment'),)
        verbose_name = 'Строительная техника всех строй управлений'
        verbose_name_plural = 'Строительная техника всех строй управлений'

class Estimate(models.Model):
    request = models.ForeignKey('Request', models.DO_NOTHING)
    material = models.ForeignKey('Materials', models.DO_NOTHING)
    material_quantity = models.FloatField(default=0.0)

    def __str__(self):
        return f"Смета для заявки {self.request.id} - {self.material_quantity} x {self.material}"

    class Meta:
        managed = False
        db_table = 'estimate'
        verbose_name = 'Смета'
        verbose_name_plural = 'Сметы'

class Materials(models.Model):
    unit_of_measure = models.ForeignKey('UnitOfMeasure', models.DO_NOTHING)
    name = models.CharField(max_length=25, default="Не указано")
    purchase_price = models.FloatField(blank=True, null=True, default=0.0)

    def __str__(self):
        return self.name

    class Meta:
        managed = False
        db_table = 'materials'
        verbose_name = 'Материал'
        verbose_name_plural = 'Материалы'

class ObjectKind(models.Model):
    name = models.CharField(max_length=25, default="Не указано")

    def __str__(self):
        return self.name

    class Meta:
        managed = False
        db_table = 'object_kind'
        verbose_name = 'Род объекта'
        verbose_name_plural = 'Рода объектов'

class Position(models.Model):
    name = models.CharField(max_length=25, default="Не указано")

    def __str__(self):
        return self.name

    class Meta:
        managed = False
        db_table = 'position'
        verbose_name = 'Должность'
        verbose_name_plural = 'Должности'

class Profession(models.Model):
    name = models.CharField(max_length=25, default="Не указано")

    def __str__(self):
        return self.name

    class Meta:
        managed = False
        db_table = 'profession'
        verbose_name = 'Профессия'
        verbose_name_plural = 'Профессии'

class Region(models.Model):
    region_name = models.CharField(max_length=25, default="Не указано")

    def __str__(self):
        return self.region_name

    class Meta:
        managed = False
        db_table = 'region'
        verbose_name = 'Регион'
        verbose_name_plural = 'Регионы'

class Request(models.Model):
    construction_site = models.ForeignKey(ConstructionSite, models.DO_NOTHING)
    request_date = models.DateField(default="01.01.2000")

    def __str__(self):
        return f"Заявка от {self.request_date} на объект {self.construction_site}"

    class Meta:
        managed = False
        db_table = 'request'
        verbose_name = 'Заявка'
        verbose_name_plural = 'Заявки'

class SectionGroup(models.Model):
    site_section = models.ForeignKey('SiteSection', models.DO_NOTHING)
    construction_site = models.ForeignKey(ConstructionSite, models.DO_NOTHING)

    def __str__(self):
        return f"Раздел {self.site_section} объекта {self.construction_site}"

    class Meta:
        managed = False
        db_table = 'section_group'
        unique_together = (('site_section', 'construction_site'),)
        verbose_name = 'Группа участков'
        verbose_name_plural = 'Группы участков'

class SiteSection(models.Model):
    construction_management = models.ForeignKey(ConstructionManagement, models.DO_NOTHING)
    name = models.CharField(max_length=25, default="Не указано")
    manager_last_name = models.CharField(max_length=25, blank=True, null=True, default="")
    manager_first_name = models.CharField(max_length=25, blank=True, null=True, default="")
    manager_middle_name = models.CharField(max_length=25, blank=True, null=True, default="")

    def __str__(self):
        if self.manager_last_name:
             return f"{self.name} ({self.manager_last_name} {self.manager_first_name})"
        return self.name

    class Meta:
        managed = False
        db_table = 'site_section'
        verbose_name = 'Участок'
        verbose_name_plural = 'Участки'

class Specialty(models.Model):
    name = models.CharField(max_length=25, default="Не указано")

    def __str__(self):
        return self.name

    class Meta:
        managed = False
        db_table = 'specialty'
        verbose_name = 'Специальность'
        verbose_name_plural = 'Специальности'

class Street(models.Model):
    street_name = models.CharField(max_length=25, default="Не указано")

    def __str__(self):
        return self.street_name

    class Meta:
        managed = False
        db_table = 'street'
        verbose_name = 'Улица'
        verbose_name_plural = 'Улицы'

class Supplier(models.Model):
    LEGAL_FORM_CHOICES = [
        ('ОАО', 'ОАО'),
        ('ООО', 'ООО'),
        ('ИП', 'ИП'),
        ('ЗАО', 'ЗАО'),
        ('ПАО', 'ПАО'),
        ('АО', 'АО'),
        ('Другое', 'Другое'),
    ]

    request = models.ForeignKey(Request, models.DO_NOTHING, blank=True, null=True)
    city = models.ForeignKey(City, models.DO_NOTHING, blank=True, null=True)
    street = models.ForeignKey(Street, models.DO_NOTHING, blank=True, null=True)
    region = models.ForeignKey(Region, models.DO_NOTHING, blank=True, null=True)
    bank = models.ForeignKey(Bank, models.DO_NOTHING, blank=True, null=True)
    name = models.CharField(max_length=25, default="Не указано")
    ok_code = models.CharField(max_length=25, blank=True, null=True, default="")
    director_last_name = models.CharField(max_length=25, blank=True, null=True, default="")
    director_first_name = models.CharField(max_length=25, blank=True, null=True, default="")
    director_middle_name = models.CharField(max_length=25, blank=True, null=True, default="")
    director_phone = models.CharField(max_length=22, blank=True, null=True, default="")
    bank_account = models.CharField(max_length=35, blank=True, null=True, default="")
    supplier_inn = models.CharField(max_length=12, blank=True, null=True, default="")
    house_number = models.CharField(max_length=10, blank=True, null=True, default="")
    legal_form = models.CharField(max_length=10, choices=LEGAL_FORM_CHOICES, blank=True, null=True, default="Другое")

    def __str__(self):
        return self.name

    class Meta:
        managed = False
        db_table = 'supplier'
        verbose_name = 'Поставщик'
        verbose_name_plural = 'Поставщики'

class Supply(models.Model):
    material = models.ForeignKey(Materials, models.DO_NOTHING)
    supplier = models.ForeignKey(Supplier, models.DO_NOTHING, blank=True, null=True)
    supply_date = models.DateField(default="01.01.2000")
    quantity = models.FloatField(default=0.0)
    purchase_price = models.FloatField(blank=True, null=True, default=0.0)

    def __str__(self):
        return f"Поставка {self.material} от {self.supplier} ({self.supply_date})"

    class Meta:
        managed = False
        db_table = 'supply'
        verbose_name = 'Поставка'
        verbose_name_plural = 'Поставки'

class Tasks(models.Model):
    WORK_TYPE_CHOICES = [
        ('Монтаж', 'Монтаж'),
        ('Демонтаж', 'Демонтаж'),
        ('Земляные работы', 'Земляные работы'),
        ('Отделочные работы', 'Отделочные работы'),
        ('Инженерные работы', 'Инженерные работы'),
        ('Другое', 'Другое'),
    ]

    construction_site = models.ForeignKey(ConstructionSite, models.DO_NOTHING)
    crew = models.ForeignKey(Crew, models.DO_NOTHING, blank=True, null=True)
    work_date = models.DateField(default="01.01.2000")
    work_type = models.CharField(max_length=20, choices=WORK_TYPE_CHOICES, blank=True, null=True, default="Другое")
    volume = models.IntegerField(blank=True, null=True, default=0)

    def __str__(self):
        return f"{self.work_type} ({self.work_date}) - {self.construction_site}"

    class Meta:
        managed = False
        db_table = 'tasks'
        verbose_name = 'Работа'
        verbose_name_plural = 'Работы'

class UnitOfMeasure(models.Model):
    name = models.CharField(max_length=25, default="Не указано")

    def __str__(self):
        return self.name

    class Meta:
        managed = False
        db_table = 'unit_of_measure'
        verbose_name = 'Единица измерения'
        verbose_name_plural = 'Единицы измерения'

class WorkReport(models.Model):
    crew = models.ForeignKey(Crew, models.DO_NOTHING)
    task = models.ForeignKey(Tasks, models.DO_NOTHING)
    completion_deadline = models.DateField(blank=True, null=True, default=None)
    materials_consumed = models.FloatField(blank=True, null=True, default=0.0)

    def __str__(self):
        return f"Отчёт бригады {self.crew} по задаче {self.task}"

    class Meta:
        managed = False
        db_table = 'work_report'
        verbose_name = 'Отчет о работах'
        verbose_name_plural = 'Отчеты о работах'

class Workplace(models.Model):
    name = models.CharField(max_length=25, default="Не указано")

    def __str__(self):
        return self.name

    class Meta:
        managed = False
        db_table = 'workplace'
        verbose_name = 'Место работы'
        verbose_name_plural = 'Места работы'
