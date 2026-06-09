export async function optionalFetchResponse(fetcher: () => Promise<Response>): Promise<Response | null> {
  try {
    return await fetcher()
  } catch {
    return null
  }
}
