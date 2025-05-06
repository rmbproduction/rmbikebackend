from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
import os
from .models import VehicleModel, Manufacturer, VehicleType

@receiver(post_save, sender=VehicleModel)
def update_setup_vehicle_data(sender, instance, created, **kwargs):
    if not created:  # Only run for new models
        return
        
    # Get the path to setup_vehicle_data.py
    setup_file_path = os.path.join(settings.BASE_DIR, 'vehicle', 'management', 'commands', 'setup_vehicle_data.py')
    
    # Read the current content of the file
    with open(setup_file_path, 'r') as file:
        content = file.read()
    
    # Find the manufacturer's models dictionary
    manufacturer_name = instance.manufacturer.name
    vehicle_type_name = instance.vehicle_type.name
    model_name = instance.name
    
    # Check if manufacturer's dictionary exists
    manufacturer_dict = f"{manufacturer_name.lower()}_models"
    if manufacturer_dict not in content:
        # Add new manufacturer dictionary
        new_dict = f"\n        {manufacturer_dict} = {{\n"
        new_dict += f"            'Bike': [],\n"
        new_dict += f"            'Scooter': [],\n"
        new_dict += "        }\n\n"
        
        # Find the position to insert the new dictionary
        insert_pos = content.find("# Create vehicle models for each manufacturer")
        if insert_pos != -1:
            content = content[:insert_pos] + new_dict + content[insert_pos:]
            
        # Add the create_vehicle_models call
        create_models_pos = content.find("create_vehicle_models(hero, hero_models)")
        if create_models_pos != -1:
            content = content[:create_models_pos] + f"create_vehicle_models({manufacturer_name.lower()}, {manufacturer_dict})\n        " + content[create_models_pos:]
    
    # Add the new model to the appropriate dictionary
    dict_start = content.find(f"{manufacturer_dict} = {{")
    if dict_start != -1:
        # Find the vehicle type list
        type_start = content.find(f"'{vehicle_type_name}': [", dict_start)
        if type_start != -1:
            # Find the end of the list
            list_end = content.find("]", type_start)
            if list_end != -1:
                # Check if model already exists
                if f"'{model_name}'" not in content[type_start:list_end]:
                    # Add the new model
                    if content[list_end-1] == "[":  # Empty list
                        new_content = f"'{model_name}'"
                    else:
                        new_content = f",\n                '{model_name}'"
                    content = content[:list_end] + new_content + content[list_end:]
    
    # Write the updated content back to the file
    with open(setup_file_path, 'w') as file:
        file.write(content) 