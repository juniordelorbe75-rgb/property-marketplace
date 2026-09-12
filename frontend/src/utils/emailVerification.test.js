import test from "node:test"
import assert from "node:assert/strict"
import { createEmailVerifier } from "./emailVerification.js"

test("effect replay shares one single-use verification request and its success", async () => {
  let calls = 0
  let complete
  const verify = createEmailVerifier((url, options) => {
    calls += 1
    assert.equal(url, "/users/email-verification/confirm")
    assert.equal(options.method, "POST")
    assert.deepEqual(JSON.parse(options.body), { token: "one-time-link" })
    return new Promise((resolve) => { complete = resolve })
  })
  const abandonedEffect = verify("one-time-link")
  const activeEffect = verify("one-time-link")
  assert.equal(abandonedEffect, activeEffect)
  assert.equal(calls, 1)
  complete(Response.json({ message: "Email verified successfully" }))
  assert.deepEqual(await activeEffect, { message: "Email verified successfully" })
  await verify("one-time-link")
  assert.equal(calls, 1)
})

test("invalid verification links keep their error without duplicate submissions", async () => {
  let calls = 0
  const verify = createEmailVerifier(async () => {
    calls += 1
    return Response.json({ detail: "This verification link is invalid or expired" }, { status: 400 })
  })
  await assert.rejects(verify("expired"), /Este enlace de verificación no es válido o ha vencido/)
  await assert.rejects(verify("expired"), /Este enlace de verificación no es válido o ha vencido/)
  assert.equal(calls, 1)
})

test("a different token gets its own result and verification pages do not share state", async () => {
  const tokens = []
  const request = async (_url, options) => {
    const { token } = JSON.parse(options.body)
    tokens.push(token)
    return Response.json({ token })
  }
  const verify = createEmailVerifier(request)
  assert.deepEqual(await verify("first"), { token: "first" })
  assert.deepEqual(await verify("second"), { token: "second" })
  await createEmailVerifier(request)("second")
  assert.deepEqual(tokens, ["first", "second", "second"])
})

test("an interrupted verification write is not automatically replayed", async () => {
  let calls = 0
  const verify = createEmailVerifier(async () => {
    calls += 1
    throw new Error("No se recibió confirmación")
  })
  const first = verify("interrupted")
  const second = verify("interrupted")
  await assert.rejects(first, /No se recibió confirmación/)
  await assert.rejects(second, /No se recibió confirmación/)
  assert.equal(calls, 1)
})
