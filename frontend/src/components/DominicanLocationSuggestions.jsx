import { DOMINICAN_PROVINCES } from "../utils/dominicanLocations"

function DominicanLocationSuggestions({ id = "dominican-location-suggestions" }) {
  return (
    <datalist id={id}>
      {DOMINICAN_PROVINCES.map((province) => (
        <option value={province} key={province} />
      ))}
    </datalist>
  )
}

export default DominicanLocationSuggestions
