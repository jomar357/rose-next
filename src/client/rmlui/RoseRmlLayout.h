#ifndef _ROSE_RML_LAYOUT_H_
#define _ROSE_RML_LAYOUT_H_

/**
 * Where the player put each RmlUi panel.
 *
 * A panel is dragged by a <handle move_target> in its markup; this remembers
 * the result in rose-next.ini ( [UI_LAYOUT] <key>=x,y ) and puts it back on
 * the next run. The stylesheet's left/top stay the default for a player who
 * never moved anything.
 *
 * Positions are screen pixels, so a saved spot can fall off a smaller screen
 * after a resolution change -- Clamp() pulls the panel back inside.
 */

namespace Rml {
class Element;
}

namespace RoseRmlLayout {

/// Apply the saved position, if any, and save it again whenever a drag of this
/// panel ends. pPanel is the move target ( a direct child of <body> ).
void Track(Rml::Element* pPanel, const char* pszKey);

/// Keep the whole panel on screen. Cheap when it already is; call per frame
/// while the panel is visible.
void Clamp(Rml::Element* pPanel, int iViewportW, int iViewportH);

} // namespace RoseRmlLayout

#endif /// _ROSE_RML_LAYOUT_H_
