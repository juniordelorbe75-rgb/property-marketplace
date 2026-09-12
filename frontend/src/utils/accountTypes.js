export const ACCOUNT_TYPES = [
  { value: "buyer", label: "Comprador", description: "Busco una propiedad para comprar o alquilar." },
  { value: "seller", label: "Vendedor", description: "Quiero publicar propiedades en venta o alquiler." },
]

export function getAccountTypeLabel(value) {
  if (value === "partner") return "Aliado"
  return ACCOUNT_TYPES.find((type) => type.value === value)?.label || "Comprador"
}
