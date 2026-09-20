import { useState } from "react"
import {
  Link,
  useLocation,
  useNavigate,
} from "react-router-dom"

import { useAuth } from "../context/AuthContext"

import {
  apiFetch,
} from "../utils/apiFetch"

import {
  readApiResponse,
} from "../utils/apiResponse"

import {
  getApiError,
} from "../utils/apiError"

import {
  getSafeReturnPath,
} from "../utils/authRedirect"

import {
  queueLoginWelcome,
} from "../utils/loginWelcomeSession"

import {
  ACCOUNT_TYPES,
} from "../utils/accountTypes"

import {
  normalizeSellerPhone,
} from "../utils/sellerDetails"

import {
  buildRegistrationPayload,
} from "../utils/registrationPayload"

import AuthLayout from "../components/AuthLayout"
import PasswordInput from "../components/PasswordInput"
import SellerFields from "../components/SellerFields"

import "./auth.css"


function compactPhone(value) {
  return (value || "")
    .replace(/[\s().-]/g, "")
}


function currentDateForInput() {
  const now = new Date()

  const year =
    now.getFullYear()

  const month =
    String(
      now.getMonth() + 1
    ).padStart(2, "0")

  const day =
    String(
      now.getDate()
    ).padStart(2, "0")

  return `${year}-${month}-${day}`
}


function Register() {
  const navigate = useNavigate()
  const location = useLocation()

  const { login } = useAuth()

  const returnTo =
    getSafeReturnPath(
      location.state?.returnTo
    )


  const [accountType, setAccountType] =
    useState("buyer")

  const [
    sellerDetails,
    setSellerDetails,
  ] = useState({
    seller_category: "",
    seller_phone: "",
    business_name: "",
  })


  const [
    phoneChallengeToken,
    setPhoneChallengeToken,
  ] = useState("")

  const [
    phoneVerificationToken,
    setPhoneVerificationToken,
  ] = useState("")

  const [
    phoneFlowPhone,
    setPhoneFlowPhone,
  ] = useState("")

  const [
    verificationCode,
    setVerificationCode,
  ] = useState("")

  const [
    sendingPhoneCode,
    setSendingPhoneCode,
  ] = useState(false)

  const [
    verifyingPhone,
    setVerifyingPhone,
  ] = useState(false)

  const [
    phoneMessage,
    setPhoneMessage,
  ] = useState("")

  const [
    phoneError,
    setPhoneError,
  ] = useState("")


  const [
    firstName,
    setFirstName,
  ] = useState("")

  const [
    middleName,
    setMiddleName,
  ] = useState("")

  const [
    lastName,
    setLastName,
  ] = useState("")

  const [
    dateOfBirth,
    setDateOfBirth,
  ] = useState("")

  const [
    bio,
    setBio,
  ] = useState("")

  const [
    email,
    setEmail,
  ] = useState("")

  const [
    password,
    setPassword,
  ] = useState("")

  const [
    confirmPassword,
    setConfirmPassword,
  ] = useState("")


  const [
    error,
    setError,
  ] = useState("")

  const [
    loading,
    setLoading,
  ] = useState(false)


  function clearPhoneVerification() {
    setPhoneChallengeToken("")
    setPhoneVerificationToken("")
    setPhoneFlowPhone("")
    setVerificationCode("")
    setPhoneMessage("")
    setPhoneError("")
  }


  function handleSellerDetailsChange(
    nextDetails
  ) {
    const nextPhone =
      compactPhone(
        nextDetails.seller_phone
      )

    if (
      phoneFlowPhone
      && nextPhone !== phoneFlowPhone
    ) {
      clearPhoneVerification()
    }

    setSellerDetails(nextDetails)
  }


  async function requestSellerPhoneCode() {
    if (
      sendingPhoneCode
      || verifyingPhone
      || loading
    ) {
      return
    }

    setPhoneError("")
    setPhoneMessage("")

    try {
      const phone =
        normalizeSellerPhone(
          sellerDetails.seller_phone
        )

      setSendingPhoneCode(true)

      const response =
        await apiFetch(
          "/users/seller-phone-verification/request",
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify({
              phone,
            }),
          },
        )

      const data =
        await readApiResponse(
          response
        )

      if (!response.ok) {
        throw new Error(
          getApiError(
            data,
            "No pudimos enviar el código de verificación",
          ),
        )
      }


      if (!data.challenge_token) {
        throw new Error(
          "El servidor no devolvió una solicitud de verificación válida."
        )
      }


      setSellerDetails(
        (current) => ({
          ...current,
          seller_phone: phone,
        }),
      )

      setPhoneFlowPhone(phone)

      setPhoneChallengeToken(
        data.challenge_token,
      )

      setPhoneVerificationToken("")
      setVerificationCode("")

      setPhoneMessage(
        data.message
        || (
          "Código enviado por SMS. " +
          "Ingrese el código para verificar el teléfono."
        ),
      )

    } catch (requestError) {
      setPhoneError(
        requestError.message
      )

    } finally {
      setSendingPhoneCode(false)
    }
  }


  async function confirmSellerPhoneCode() {
    if (
      verifyingPhone
      || sendingPhoneCode
      || loading
    ) {
      return
    }

    setPhoneError("")

    try {
      const phone =
        normalizeSellerPhone(
          sellerDetails.seller_phone
        )

      if (
        !phoneChallengeToken
        || !phoneFlowPhone
      ) {
        throw new Error(
          "Primero solicite un código de verificación."
        )
      }

      if (phone !== phoneFlowPhone) {
        throw new Error(
          "El teléfono cambió. Solicite un código nuevo."
        )
      }

      const code =
        verificationCode.trim()

      if (
        !/^[0-9]{4,10}$/.test(code)
      ) {
        throw new Error(
          "Ingrese el código numérico recibido por SMS."
        )
      }


      setVerifyingPhone(true)

      const response =
        await apiFetch(
          "/users/seller-phone-verification/confirm",
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify({
              challenge_token:
                phoneChallengeToken,

              code,
            }),
          },
        )

      const data =
        await readApiResponse(
          response
        )

      if (!response.ok) {
        throw new Error(
          getApiError(
            data,
            "No pudimos verificar el teléfono",
          ),
        )
      }


      if (
        !data.phone_verification_token
      ) {
        throw new Error(
          "El servidor no confirmó la verificación del teléfono."
        )
      }


      setPhoneVerificationToken(
        data.phone_verification_token,
      )

      setPhoneChallengeToken("")
      setVerificationCode("")

      setPhoneMessage(
        data.message
        || "Teléfono verificado correctamente.",
      )

    } catch (verificationError) {
      setPhoneError(
        verificationError.message
      )

    } finally {
      setVerifyingPhone(false)
    }
  }


  async function handleRegister(event) {
    event.preventDefault()

    if (loading) {
      return
    }

    setError("")


    if (
      password !== confirmPassword
    ) {
      setError(
        "Las contraseñas no coinciden."
      )

      return
    }


    setLoading(true)

    try {
      const payload =
        buildRegistrationPayload({
          accountType,

          firstName,
          middleName,
          lastName,
          dateOfBirth,
          bio,
          email,
          password,

          sellerDetails,

          phoneVerificationToken,

          verifiedSellerPhone:
            phoneVerificationToken
              ? phoneFlowPhone
              : "",
        })


      const response =
        await apiFetch(
          "/users/",
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body:
              JSON.stringify(
                payload
              ),
          },
        )


      const data =
        await readApiResponse(
          response
        )


      if (!response.ok) {
        throw new Error(
          getApiError(
            data,
            "No pudimos completar el registro",
          ),
        )
      }


      const loginResponse =
        await apiFetch(
          "/users/login",
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body:
              JSON.stringify({
                email:
                  payload.email,

                password,
              }),
          },
        )


      const loginData =
        await readApiResponse(
          loginResponse
        )


      if (!loginResponse.ok) {
        throw new Error(
          getApiError(
            loginData,
            (
              "La cuenta fue creada, " +
              "pero no pudimos iniciar " +
              "la sesión automáticamente"
            ),
          ),
        )
      }


      if (!loginData.access_token) {
        throw new Error(
          "La cuenta fue creada, pero el servidor no devolvió una sesión válida."
        )
      }


      login(
        loginData.access_token
      )

      queueLoginWelcome("new")

      navigate(
        returnTo,
        {
          replace: true,
        },
      )

    } catch (registrationError) {
      console.error(
        "Registration error:",
        registrationError,
      )

      setError(
        registrationError.message
      )

    } finally {
      setLoading(false)
    }
  }


  const sellerPhoneVerified =
    Boolean(
      accountType === "seller"
      && phoneVerificationToken
      && phoneFlowPhone
    )


  return (
    <AuthLayout wide>

      <p className="auth-card-eyebrow">
        Únase al mercado
      </p>


      <h1>
        Cree su cuenta
      </h1>


      <p className="auth-intro">
        Busque su próximo hogar o publique
        propiedades en HabitaRD.
      </p>


      <form
        className="auth-form"
        onSubmit={handleRegister}
      >

        <div className="auth-field">

          <label htmlFor="register-account-type">
            ¿Qué desea hacer en HabitaRD?
          </label>


          <select
            id="register-account-type"
            value={accountType}

            onChange={(event) => {
              setAccountType(
                event.target.value
              )

              setError("")
            }}

            required
          >

            {ACCOUNT_TYPES.map(
              (type) => (
                <option
                  key={type.value}
                  value={type.value}
                >
                  {type.label}
                </option>
              ),
            )}

          </select>


          <small>
            {
              accountType === "seller"
                ? (
                  "Quiero publicar propiedades " +
                  "en venta o alquiler y " +
                  "administrar mis anuncios."
                )
                : (
                  "Quiero buscar propiedades, " +
                  "guardar favoritos y " +
                  "contactar propietarios."
                )
            }
          </small>

        </div>


        <div className="auth-field">

          <label htmlFor="register-first-name">
            Nombre
          </label>

          <input
            id="register-first-name"
            type="text"
            autoComplete="given-name"

            value={firstName}

            onChange={(event) =>
              setFirstName(
                event.target.value
              )
            }

            maxLength={100}
            required
          />

        </div>


        <div className="auth-field">

          <label htmlFor="register-middle-name">
            Segundo nombre{" "}

            <span>
              (opcional)
            </span>
          </label>

          <input
            id="register-middle-name"
            type="text"
            autoComplete="additional-name"

            value={middleName}

            onChange={(event) =>
              setMiddleName(
                event.target.value
              )
            }

            maxLength={100}
          />

        </div>


        <div className="auth-field">

          <label htmlFor="register-last-name">
            Apellido
          </label>

          <input
            id="register-last-name"
            type="text"
            autoComplete="family-name"

            value={lastName}

            onChange={(event) =>
              setLastName(
                event.target.value
              )
            }

            maxLength={100}
            required
          />

        </div>


        <div className="auth-field">

          <label htmlFor="register-date-of-birth">
            Fecha de nacimiento
          </label>

          <input
            id="register-date-of-birth"
            type="date"
            autoComplete="bday"

            value={dateOfBirth}

            onChange={(event) =>
              setDateOfBirth(
                event.target.value
              )
            }

            max={currentDateForInput()}
            required
          />

        </div>


        <div className="auth-field">

          <label htmlFor="register-bio">
            Sobre usted{" "}

            <span>
              (opcional)
            </span>
          </label>

          <textarea
            id="register-bio"

            value={bio}

            onChange={(event) =>
              setBio(
                event.target.value
              )
            }

            maxLength={1000}
            rows={5}

            placeholder={
              "Cuénteles un poco sobre usted " +
              "a otros miembros del mercado."
            }
          />

          <small>
            {bio.length}/1000 caracteres
          </small>

        </div>


        {accountType === "seller" && (
          <>
            <SellerFields
              idPrefix="register"

              details={
                sellerDetails
              }

              onChange={
                handleSellerDetailsChange
              }

              disabled={
                loading
                || sendingPhoneCode
                || verifyingPhone
              }

              phoneHelp={
                sellerPhoneVerified
                  ? (
                    "Teléfono verificado. " +
                    "Si lo cambia deberá verificarlo nuevamente."
                  )
                  : (
                    "Incluya el código de país. " +
                    "Ejemplo: +1 809 555 0123."
                  )
              }
            />


            <div className="auth-field">

              <label>
                Verificación del teléfono
              </label>

              <small>
                HabitaRD enviará un código por SMS
                al teléfono indicado.
              </small>


              <button
                type="button"
                className="auth-link-button"

                onClick={
                  requestSellerPhoneCode
                }

                disabled={
                  loading
                  || sendingPhoneCode
                  || verifyingPhone
                  || !sellerDetails.seller_phone
                }
              >
                {
                  sendingPhoneCode
                    ? "Enviando código..."
                    : (
                      phoneVerificationToken
                        ? "Enviar un código nuevo"
                        : (
                          phoneChallengeToken
                            ? "Reenviar código"
                            : "Enviar código por SMS"
                        )
                    )
                }
              </button>

            </div>


            {
              phoneChallengeToken
              && !phoneVerificationToken
              && (
                <div className="auth-field">

                  <label htmlFor="seller-verification-code">
                    Código recibido por SMS
                  </label>

                  <input
                    id="seller-verification-code"

                    type="text"

                    inputMode="numeric"
                    autoComplete="one-time-code"

                    pattern="[0-9]{4,10}"
                    maxLength={10}

                    value={
                      verificationCode
                    }

                    onChange={(event) =>
                      setVerificationCode(
                        event.target.value
                          .replace(
                            /\D/g,
                            "",
                          )
                      )
                    }

                    placeholder="123456"
                  />


                  <button
                    type="button"
                    className="auth-link-button"

                    onClick={
                      confirmSellerPhoneCode
                    }

                    disabled={
                      loading
                      || verifyingPhone
                      || sendingPhoneCode
                      || !verificationCode
                    }
                  >
                    {
                      verifyingPhone
                        ? "Verificando..."
                        : "Verificar teléfono"
                    }
                  </button>

                </div>
              )
            }


            {phoneMessage && (
              <p
                className="auth-success"
                role="status"
              >
                {phoneMessage}
              </p>
            )}


            {phoneError && (
              <p
                className="auth-error"
                role="alert"
              >
                {phoneError}
              </p>
            )}
          </>
        )}


        <div className="auth-field">

          <label htmlFor="register-email">
            Correo electrónico
          </label>

          <input
            id="register-email"
            type="email"
            autoComplete="email"

            value={email}

            onChange={(event) =>
              setEmail(
                event.target.value
              )
            }

            maxLength={255}
            required
          />

        </div>


        <PasswordInput
          id="register-password"

          label="Contraseña"

          value={password}

          onChange={(event) =>
            setPassword(
              event.target.value
            )
          }

          autoComplete="new-password"

          describedBy={
            "new-password-help"
          }

          minLength={8}
        />


        <small
          id="new-password-help"
          className="password-help"
        >
          Use al menos 8 caracteres.
          Utilice una contraseña única
          para HabitaRD.
        </small>


        <div>

          <PasswordInput
            id="register-confirm-password"

            label="Confirmar contraseña"

            value={confirmPassword}

            onChange={(event) =>
              setConfirmPassword(
                event.target.value
              )
            }

            autoComplete="new-password"

            minLength={8}

            invalid={
              Boolean(confirmPassword)
              && password
                !== confirmPassword
            }

            describedBy={
              "confirm-password-help"
            }
          />


          <small
            id="confirm-password-help"
          >
            {
              confirmPassword
              && password
                !== confirmPassword

                ? (
                  "Las contraseñas " +
                  "no coinciden."
                )

                : (
                  "Escriba nuevamente " +
                  "la misma contraseña."
                )
            }
          </small>

        </div>


        {error && (
          <p
            className="auth-error"
            role="alert"
          >
            {error}
          </p>
        )}


        <button
          type="submit"
          className="auth-submit"

          disabled={
            loading
            || sendingPhoneCode
            || verifyingPhone
            || !confirmPassword
            || password !== confirmPassword
            || (
              accountType === "seller"
              && !sellerPhoneVerified
            )
          }
        >
          {
            loading
              ? "Creando cuenta..."
              : "Crear cuenta"
          }
        </button>


        {
          accountType === "seller"
          && !sellerPhoneVerified
          && (
            <small>
              Debe verificar el teléfono
              antes de crear una cuenta
              de vendedor.
            </small>
          )
        }

      </form>


      <p className="auth-switch">
        ¿Ya tiene una cuenta?{" "}

        <Link
          to="/login"
          state={{ returnTo }}
        >
          Iniciar sesión
        </Link>
      </p>

    </AuthLayout>
  )
}


export default Register