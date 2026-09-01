export function buildPropertyStatusUpdate(property, status) {
  return {
    title: property.title,
    description: property.description || "",
    image_url: property.image_url,
    image_urls: property.image_urls || (property.image_url ? [property.image_url] : []),
    price: property.price,
    currency: property.currency,
    listing_type: property.listing_type || "sale",
    amenities: property.amenities || [],
    location: property.location,
    property_type: property.property_type,
    bedrooms: property.bedrooms,
    bathrooms: property.bathrooms,
    square_feet: property.square_feet || 0,
    status,
  }
}
