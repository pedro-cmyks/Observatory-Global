export interface ThreadGeographyInput {
  top_countries?: string[]
  top_country_names?: string[]
  subject_countries?: string[]
  subject_country_names?: string[]
  subject_geography_status?: string | null
}

export interface ThreadCountryPresentation {
  kind: 'subject' | 'coverage'
  label: 'Verified subject' | 'Coverage'
  codes: string[]
  names: string[]
}

/** Keep subject identity separate from the countries carrying coverage. */
export function threadCountryPresentation(
  thread: ThreadGeographyInput,
): ThreadCountryPresentation {
  const subjectCodes = thread.subject_countries ?? []
  const useSubject = thread.subject_geography_status === 'verified' && subjectCodes.length > 0
  return {
    kind: useSubject ? 'subject' : 'coverage',
    label: useSubject ? 'Verified subject' : 'Coverage',
    codes: useSubject ? subjectCodes : (thread.top_countries ?? []),
    names: useSubject ? (thread.subject_country_names ?? []) : (thread.top_country_names ?? []),
  }
}
