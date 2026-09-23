#ifndef _ROSE_RML_ICONS_H_
#define _ROSE_RML_ICONS_H_

/**
 * Game icons ( item, skill, status ... ) inside RmlUi documents.
 *
 * The icons live in the legacy TSI atlases ( IMAGE_RES_* modules ). Rather
 * than re-cut them, a panel shows one as
 *
 *     <img data-attr-src="icon.src" data-attr-rect="icon.rect"/>
 *
 * and this resolves a sprite index to that pair: the atlas DDS, which the
 * renderer loads through the VFS, and the sprite's pixel rectangle in it.
 * RmlUi caches textures by source, so every icon on one sheet shares one
 * texture.
 */

#include <RmlUi/Core/Types.h>

namespace RoseRmlIcons {

/// iModule is an IMAGE_RES_* id, iIndex a sprite index in it. Returns false
/// ( and leaves the outputs empty ) for an index the atlas does not have.
bool Resolve(int iModule, int iIndex, Rml::String& strSrc, Rml::String& strRect);

} // namespace RoseRmlIcons

#endif /// _ROSE_RML_ICONS_H_
