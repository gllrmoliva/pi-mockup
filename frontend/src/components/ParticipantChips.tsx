import type { Participant } from '../api/types';
import { initials, roleLabels } from '../utils/format';

type ParticipantChipsProps = {
    participants: Participant[];
    showRole?: boolean;
};

export function ParticipantChips({ participants, showRole = true }: ParticipantChipsProps) {
    return (
        <ul className="participants" aria-label="Participantes del proyecto">
            {participants.map((participant) => (
                <li className="participant" key={participant.id}>
                    <span className="avatar" aria-hidden="true">
                        {initials(participant.name)}
                    </span>
                    <span>{participant.name}</span>
                    {showRole ? (
                        <span className="participant__role">{roleLabels[participant.role]}</span>
                    ) : null}
                </li>
            ))}
        </ul>
    );
}
