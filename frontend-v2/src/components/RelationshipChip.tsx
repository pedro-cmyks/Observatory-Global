import { relationshipChip, type TopicRelationship } from '../lib/topicRelationship'

// #168 attention-relationship badge (TierChip pattern: logic in the lib, this
// is the one thin render site). Compact mode (list rows) renders only the
// differentiating classes; full mode (ThemeDetail) renders every type.
// No data / media-led-in-compact / unknown type → renders NOTHING.
export function RelationshipChip({
    rel,
    compact,
}: {
    rel: TopicRelationship | null | undefined
    compact?: boolean
}) {
    const model = relationshipChip(rel, { compact })
    if (!model) return null
    return (
        <span className={`rel-chip ${model.className}`} data-tip={model.tip}>
            {model.text}
        </span>
    )
}
