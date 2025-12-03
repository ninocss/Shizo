from util.constants import *

TEXTS = {
    
    "BOT_NAME": "Shizo",
    # First Ticket embed texts
    "SUPPORT_HEADER_TEXT": "🎫 Support",
    "EMBED_CREATED": "Embed wurde gesendet",
    "TICKET_CREATION_EMBED_TEXT": "Hast du Fragen oder möchtest etwas anmerken? Öffne jetzt ein **Support-Ticket**, um Kontakt mit unserem Team aufzunehmen. Es wird so schnell es geht jemand antworten. Du brauchst niemanden vom Team anzupingen.",
    "WHAT_NEXT": "Was als nächstes?",
    "WHAT_NEXT_VALUE": 'Wähle eine **Kategorie** aus dem **Drop-Down Menü** aus, um weitere Informationen zu erhalten und um dein **Ticket anzupassen**.',
    
    # Error Messages
    "ERROR": "❌ Fehler",
    "NO_PERMISSION_TITLE": "Keine Berechtigung",
    "NO_PERMISSION": "Du hast keine Berechtigung für diesen Befehl.",
    "CAN_ONLY_BE_USED_IN_THREAD": "Dieser Befehl kann nur in einem Ticket-Thread verwendet werden.",
    "NO_MEMBER": "Fehler: Der Member existiert nicht.",
    "MEMBER_NOT_FOUND": "Fehler: Der Member konnte nicht gefunden werden.",
    
    # Close Embed
    "CLOSE_EMBED_DESC": f'Schließe das Ticket mit {LOCK_EMOJI} und bestätige mit **"Ja"**, oder brich mit **"Nein"** ab.\n Um das Ticket mit einem **Grund** zuschließen, drücke auf {LOCK_W_REASON_EMOJI} und gib deinen Grund an.',
    "TICKET_OVERVIEW_TITLE": "🎫 Ticket Übersicht",
    
    # Embed Footer
    "EMBED_FOOTER": "Ticket System",
    
    # Ticket Messages
    "TICKET_CREATION_SUCCESS": "Ticket erstellt in {thread}!",
    "TICKET_CREATION_ERROR": "Fehler beim Erstellen des Tickets.",
    "TICKET_CLOSE_CONFIRMATION": "> {user} Bist du dir sicher, dass du das Ticket schließen möchtest?",
    "TICKET_CLOSE_WITH_REASON_CONFIRMATION": "> {user} Bist du dir sicher, dass du das Ticket mit dem Grund: ```{reason}``` schließen möchtest?",
    "DEFAULT_HELP_MESSAGE": "Es wird dir so schnell wie möglich geholfen!",
    "TICKET_CLOSED_TIMEOUT": "> Ticket geschlossen aus folgendem Grund: ```Time-Out nach 30 Tagen.```",
    "TICKET_CLOSED_BY": "> Ticket geschlossen von **{user_display}** *({user_name})*",
    "TICKET_CLOSED_BY_REASON": "> Ticket geschlossen von **{user_display}** *({user_name})* aus folgendem Grund: ```{reason}```",
    "TICKET_REOPENED": "> {user} Das Ticket wurde neu eröffnet.",
    "SETUP_MESSAGES_DELETED": "> Alle setup Nachrichten im Ticket wurden gelöscht.",
    
    # Button Labels
    "CANCEL_BUTTON_LABEL": "Abbrechen",
    "CLOSE_TICKET_BUTTON": "Ticket schließen",
    "CLOSE_TICKET_REASON_BUTTON": "Ticket mit Grund schließen",
    "YES_CLOSE_BUTTON": "Ja, schließen",
    "NO_BUTTON": "Nein",
    "DELETE_BUTTON": "Löschen",
    "REOPEN_BUTTON": "Neu eröffnen",
    "TRANSCRIPT_BUTTON": "Transkribieren",
    "ARCHIVE_BUTTON": "Archivieren",
    "YES_DELETE_BUTTON": "Ja, löschen",
    
    # Confirmation Messages
    "CLOSE_CONFIRMATION": "> {user} Bist du dir sicher, dass du das Ticket schließen möchtest?",
    "DELETE_CONFIRMATION": "> {user} Möchtest du dieses Ticket wirklich löschen?",
    
    # Dropdown Options
    "DROPDOWN_PLACEHOLDER": "Wähle eine Option",
    "DISCORD_GENERAL": "Discord",
    "MINECRAFT_GENERAL": "Minecraft",
    "SURVIVAL_AREA": "Bereich sichern",
    "CREATIVE_PLOT": "Parzellen (übertragen)",
    "UNBAN_REQUEST": "Entbannungsantrag",
    "OTHER": "Sonstiges",
    
    # Ticket Category Messages
    "GENERAL_DISCORD_HELP": "Wie können wir dir helfen? Was ist dein Anliegen?",
    "GENERAL_MINECRAFT_HELP": "Wie können wir dir helfen? Was ist dein Anliegen?",
    "UNBAN_REQUEST_MESSAGE": "Schreibe nun dein Entbannungs-Antrag. Wir werden ihn intern besprechen und uns bei dir hier melden.",
    "OTHER_HELP": "Wie können wir dir helfen? Was ist dein Anliegen?",
    
    # Modal Titles and Labels
    "ARCHIVE_TICKET_MODAL_TITLE": "Archiviere das Ticket",
    "RENAME_TICKET_LABEL": "Soll das Ticket einen anderen Namen haben?",
    "RENAME_TICKET_PLACEHOLDER": "Der neue Name des Tickets",
    "ARCHIVE_ERROR": "Fehler beim Archivieren des Tickets: {error}",
    
    "TICKET_DESCRIPTION_MODAL_TITLE": "Beschreibung des Tickets",
    "TICKET_DESCRIPTION_LABEL": "Beschreibung des Tickets",
    "DESCRIPTION_ERROR": "Fehler beim ändern der Beschreibung: {error}",
    
    "CLOSE_TICKET_MODAL_TITLE": "Ticket schließen",
    "CLOSE_REASON_LABEL": "Grund",
    "CLOSE_REASON_PLACEHOLDER": "Gib den Grund für das Schließen des Tickets an.",
    
    "AREA_SAVING_MODAL_TITLE": "Bereich Sichern",
    "AREA_SAVING_TITLE": "Bereich Sichern",
    "WORLD_LABEL": "Welt",
    "WORLD_PLACEHOLDER": "Die Welt, e.g. Overworld, Nether, End",
    "COORDINATES_LABEL": "Koordinaten",
    "COORDINATES_PLACEHOLDER": "120 60 120 bis 200 70 200",
    
    "PLOT_TRANSFER_MODAL_TITLE": "Parzelle übertragen",
    "PLOT_TRANSFER_TITLE": "Parzelle übertragen",
    "INGAME_NAME_LABEL": "Ingame Name",
    "INGAME_NAME_PLACEHOLDER": "Der Name deines Minecraft Accounts",
    "CANSTEIN_NAME_LABEL": "Canstein Nummer",
    "CANSTEIN_NAME_PLACEHOLDER": "Die Nummer des benutzten Canstein Accounts",
    
    # Embed Titles and Descriptions
    "TICKET_CLOSED_EMBED_TITLE": "Ticket geschlossen - {channel_name}",
    "TICKET_CLOSED_EMBED_DESC": "**Geschlossen von:** {user}\n**Grund:** {reason}\n**Server:** {guild_name}",
    
    # Creation texts
    "LABEL_DISCORD": "Discord",
    "LABEL_MINECRAFT": "Minecraft",
    "LABEL_BEREICH": "Bereich sichern",
    "LABEL_PARZELLE": "Parzellen (übertragen)",
    "LABEL_ENTBANNUNG": "Entbannungsantrag",
    "LABEL_SONSTIGES": "Sonstiges",
    
    "PLACEHOLDER_TEXT": "Wähle eine Option",
    
    "TITLE_DISCORD": "Discord",
    "TITLE_MINECRAFT": "Minecraft",
    "TITLE_ENTBANNUNG": "Entbannungsantrag",
    "TITLE_BEREICH": "Bereich sichern",
    "TITLE_PARZELLE": "Parzellen (übertragen)",
    "TITLE_SONSTIGES": "Sonstiges",
    
    "MESSAGE_GENERAL": "Wie können wir dir helfen? Was ist dein Anliegen?",
    "MESSAGE_ENTBANNUNG": "Schreibe nun dein Entbannungs-Antrag. Wir werden ihn intern besprechen und uns bei dir hier melden.",
    
    "NO_MEMBER": "> Fehler: Member wurde nicht gefunden.",
    "NO_PERMISSION": "> Du hast keine Berechtigung, diese Aktion auszuführen.",
    "SAME_VC": "> Du musst dich im selben Sprachkanal wie der Bot befinden, um diesen Befehl zu nutzen.",

    "TICKET_CLOSE_PROMPT": "<@{ticket_creator}> Wenn du keine weiteren Fragen hast, kannst du das Ticket gerne schließen!"
}

globals().update({key: value for key, value in TEXTS.items()})