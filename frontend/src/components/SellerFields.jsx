import { SELLER_CATEGORIES } from "../utils/sellerDetails"
import "./SellerFields.css"

export default function SellerFields({ idPrefix, details, onChange, disabled = false, phoneHelp = "Incluya el código de país." }) {
  function change(field, value) {
    onChange({ ...details, [field]: value })
  }
  return (
    <fieldset className="seller-fields" disabled={disabled} aria-describedby={`${idPrefix}-seller-help`}>
      <legend>Datos del vendedor</legend>
      <p id={`${idPrefix}-seller-help`}>Estos datos de contacto se guardan en su cuenta y no se muestran en su perfil público.</p>
      <label htmlFor={`${idPrefix}-seller-category`}>Tipo de vendedor
        <select id={`${idPrefix}-seller-category`} value={details.seller_category || ""} onChange={(event) => change("seller_category", event.target.value)} required>
          <option value="" disabled>Seleccione una opción</option>
          {SELLER_CATEGORIES.map((category) => <option key={category.value} value={category.value}>{category.label}</option>)}
        </select>
      </label>
      <label htmlFor={`${idPrefix}-seller-phone`}>Teléfono de contacto
        <input id={`${idPrefix}-seller-phone`} type="tel" autoComplete="tel" value={details.seller_phone || ""} onChange={(event) => change("seller_phone", event.target.value)} maxLength={40} placeholder="+1 809 555 0123" aria-describedby={`${idPrefix}-phone-help`} required />
        <small id={`${idPrefix}-phone-help`}>{phoneHelp}</small>
      </label>
      <label htmlFor={`${idPrefix}-business-name`}>Nombre de la empresa (opcional)
        <input id={`${idPrefix}-business-name`} type="text" autoComplete="organization" value={details.business_name || ""} onChange={(event) => change("business_name", event.target.value)} maxLength={150} />
      </label>
    </fieldset>
  )
}
