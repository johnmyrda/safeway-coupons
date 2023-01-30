
brands = {
    "safeway" : "www.safeway.com",
    "jewel-osco" : "www.jewelosco.com"
}

def get_url(brand: str):
    return brands.get(brand, "www.safeway.com")