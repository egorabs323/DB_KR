from django.contrib import admin
from .models import *

for model in [Bank, City, Classification, Client, ConstructionManagement, ConstructionSite,
              Contract, Crew, CrewComposition, CrewGroup, Department, Employee, EmploymentRecord,
              Equipment, EquipmentAtSite, EquipmentManagement, Estimate, Materials, ObjectKind,
              Position, Profession, Region, Request, SectionGroup, SiteSection, Specialty, Street,
              Supplier, Supply, Tasks, UnitOfMeasure, WorkReport, Workplace]:
    admin.site.register(model)