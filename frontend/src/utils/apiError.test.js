import assert from "node:assert/strict"
import test from "node:test"

import {
  getApiError,
  translateApiMessage,
} from "./apiError.js"


test(
  "translates known server messages without changing unknown details",
  () => {
    assert.equal(
      translateApiMessage(
        "Property not found"
      ),
      "Propiedad no encontrada",
    )

    assert.equal(
      translateApiMessage(
        "Mensaje propio"
      ),
      "Mensaje propio",
    )
  },
)


test(
  "translates pydantic value errors",
  () => {
    assert.equal(
      translateApiMessage(
        "Value error, Enter a valid email address"
      ),
      "Ingrese un correo electrónico válido",
    )

    assert.equal(
      translateApiMessage(
        "Value error, Date of birth cannot be in the future"
      ),
      "La fecha de nacimiento no puede estar en el futuro",
    )
  },
)


test(
  "translates forbidden unexpected fields",
  () => {
    assert.equal(
      translateApiMessage(
        "Extra inputs are not permitted"
      ),
      "La solicitud contiene un campo no permitido",
    )
  },
)


test(
  "presents support identifiers and validation details in Spanish",
  () => {
    assert.equal(
      getApiError(
        {
          detail:
            "Invalid email or password",

          request_id:
            "abc-123",
        },
        "Error",
      ),
      (
        "El correo o la contraseña no son válidos " +
        "Código de soporte: abc-123"
      ),
    )


    assert.equal(
      getApiError(
        {
          detail: [
            {
              msg:
                "Message cannot be empty",
            },
          ],
        },
        "Error",
      ),
      "El mensaje no puede estar vacío",
    )
  },
)