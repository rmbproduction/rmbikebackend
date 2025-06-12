# Spare Parts Management Commands

This directory contains management commands for working with the Spare Parts module in the Repair My Bike application.

## Available Commands

### 1. Create Spare Parts

```bash
python manage.py create_spare_parts
```

This command creates sample spare part categories and parts in the database. It adds:

- 7 categories (Engine Parts, Body Parts, Lighting, Electrical, Brakes, Suspension, Accessories)
- 15 spare parts with complete details (name, description, features, price, etc.)

The command is idempotent - it will skip parts that already exist in the database.

### 2. Add Spare Part Images

```bash
python manage.py add_spare_part_images
```

This command adds placeholder images to any spare parts that don't have a main image. In a production environment, you would replace the placeholder images with real product photos.

## Running the Commands

To set up the spare parts data completely, run the commands in this order:

1. First create the parts:
   ```bash
   python manage.py create_spare_parts
   ```

2. Then add images:
   ```bash
   python manage.py add_spare_part_images
   ```

## Notes

- The `main_image` field in the SparePart model uses Cloudinary for image storage.
- The commands generate random values for some fields like stock_quantity and specifications.
- If you want to modify the parts being created, edit the `spare_parts` list in the `create_spare_parts.py` file. 