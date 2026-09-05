import { Link, useLocation } from "react-router-dom"
import "./TrustPage.css"

const pages = {
  "/about": {
    eyebrow: "Sobre el mercado",
    title: "Una forma más clara de descubrir propiedades dominicanas",
    intro: "HabitaRD es un mercado inmobiliario en desarrollo operado por Damaso Del Orbe. Nuestro propósito es permitir que cualquier persona explore viviendas y proyectos disponibles en toda la República Dominicana antes de crear una cuenta.",
    sections: [
      ["Lo que estamos construyendo", "Una experiencia profesional de búsqueda que pueda combinar anuncios administrados por propietarios con inventario suministrado por corredores, desarrolladores, asociaciones y aliados tecnológicos autorizados."],
      ["Nuestra responsabilidad", "Mostramos claramente la fuente del inventario de aliados, lo mantenemos separado de los anuncios administrados por propietarios y retiramos los registros cuando termina la autorización o ya no podemos confirmar su disponibilidad."],
      ["Contacto", "Puede enviar sus preguntas comerciales o sobre el mercado a juniordelorbe75@gmail.com, o comunicarse por teléfono al +1 849-504-7853."],
    ],
  },
  "/data-partners": {
    eyebrow: "Datos y aliados",
    title: "Datos inmobiliarios utilizados con autorización",
    intro: "Que una propiedad sea visible públicamente no concede automáticamente derechos para republicarla. Solicitamos autorización escrita antes de mostrar anuncios, fotografías o información de contacto de un proveedor.",
    sections: [
      ["Cómo funcionan los anuncios de aliados", "Los datos autorizados conservan la identidad del proveedor, la referencia original, la atribución, la fecha de actualización y un enlace hacia la fuente oficial. Los anuncios de proveedores no sustituyen ni aparentan ser anuncios administrados por propietarios."],
      ["Controles de publicación", "Ningún proveedor se publica hasta que un administrador registra su permiso. Las autorizaciones revocadas o vencidas, el inventario retirado y los datos desactualizados se eliminan de la búsqueda pública, conservando un historial interno de auditoría."],
      ["Correcciones y retiros", "Los proveedores, agentes, desarrolladores y titulares de derechos pueden solicitar una corrección o retiro en cualquier momento escribiendo a juniordelorbe75@gmail.com. Incluya el enlace o referencia del anuncio y explique su relación con la propiedad."],
      ["Conviértase en aliado de datos", "Aceptamos fuentes autorizadas mediante JSON, XML, MLS, CRM o datos directos de desarrolladores con cobertura en la República Dominicana. La solicitud debe indicar el territorio disponible, frecuencia de actualización, derechos sobre imágenes, atribución requerida y reglas para dirigir las consultas."],
    ],
  },
  "/privacy": {
    eyebrow: "Aviso de privacidad",
    title: "Decisiones de privacidad fáciles de comprender",
    intro: "Este aviso describe las prácticas actuales del mercado mientras el servicio se encuentra en desarrollo. Será actualizado antes de introducir nuevos usos importantes de la información personal.",
    sections: [
      ["Información que usted proporciona", "Procesamos el registro de cuenta, preferencias del perfil, anuncios, favoritos, consultas, reportes y comunicaciones para ofrecer las funciones que usted solicita. La información del perfil público permanece limitada por sus decisiones de visibilidad."],
      ["Seguridad y conservación", "Las contraseñas se almacenan mediante resúmenes criptográficos seguros, las acciones autenticadas requieren sesiones protegidas y las respuestas sensibles no se guardan en caché. Conservamos la información solo durante el tiempo necesario para operar el mercado, proteger a sus usuarios, resolver disputas y cumplir obligaciones legales."],
      ["Datos de aliados", "Los registros provenientes de fuentes inmobiliarias identifican a la empresa que los suministra. No interpretamos la información pública de contacto de un propietario como permiso para copiarla o republicarla."],
      ["Sus opciones", "Puede actualizar la visibilidad de su perfil y la información de su cuenta desde la página Mi cuenta. Envíe cualquier solicitud de privacidad, eliminación, corrección o datos de proveedores a juniordelorbe75@gmail.com."],
    ],
  },
  "/terms": {
    eyebrow: "Términos del mercado",
    title: "Utilice el mercado de manera responsable",
    intro: "Al utilizar HabitaRD, usted acepta emplear la información inmobiliaria para búsquedas y comunicaciones legítimas. Los anuncios son informativos y no constituyen asesoría legal, financiera, registral, de tasación ni de inversión.",
    sections: [
      ["Verifique antes de actuar", "Antes de realizar cualquier transacción, confirme de manera independiente el precio, disponibilidad, medidas, titularidad, permisos, tratamiento fiscal y condición de la propiedad con la fuente autorizada y profesionales dominicanos calificados."],
      ["Responsabilidad sobre los anuncios", "Quienes publiquen anuncios administrados por propietarios deben estar autorizados y proporcionar información veraz y legal. Se prohíben el fraude, la suplantación, el contenido discriminatorio, la automatización maliciosa y las copias no autorizadas."],
      ["Inventario de terceros", "Los anuncios de aliados están sujetos a los términos y a la disponibilidad de su proveedor. La atribución y los enlaces de origen no significan que el mercado sea dueño de la propiedad ni que represente a todas las partes de una transacción."],
      ["Seguridad y retiro", "El mercado puede retener o retirar contenido disputado, inseguro, desactualizado, no autorizado o engañoso. Reporte cualquier preocupación mediante las herramientas del anuncio o escriba a juniordelorbe75@gmail.com."],
    ],
  },
}

function TrustPage() {
  const { pathname } = useLocation()
  const page = pages[pathname] || pages["/about"]

  return (
    <main className="trust-page">
      <div className="trust-page-heading">
        <span>{page.eyebrow}</span>
        <h1>{page.title}</h1>
        <p>{page.intro}</p>
      </div>
      <div className="trust-page-sections">
        {page.sections.map(([heading, body]) => (
          <section key={heading}>
            <h2>{heading}</h2>
            <p>{body}</p>
          </section>
        ))}
      </div>
      <aside className="trust-page-note">
        <strong>¿Busca una propiedad?</strong>
        <span>Puede explorar el mercado sin crear una cuenta.</span>
        <Link to="/search">Buscar propiedades</Link>
      </aside>
    </main>
  )
}

export default TrustPage
