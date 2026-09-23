#include "stdafx.h"

#include "RoseRmlIcons.h"

#include "../interface/io_imageres.h"

#include <stdio.h>

namespace RoseRmlIcons {

bool
Resolve(int iModule, int iIndex, Rml::String& strSrc, Rml::String& strRect) {
    strSrc.clear();
    strRect.clear();

    CImageRes* pRes = CImageResManager::GetSingleton().GetImageRes(iModule);
    if (pRes == NULL || iIndex < 0 || iIndex >= pRes->GetSpriteCount())
        return false;

    const stSprite* pSprite = pRes->GetSprite(iIndex);
    const stTexture* pTexture = pRes->GetTexture(iIndex);
    if (pSprite == NULL || pTexture == NULL || pTexture->m_szName[0] == '\0')
        return false;

    /// Same folder CImageRes::LoadRES reads the sheets from. The "3DData"
    /// prefix is what RoseRmlSystem::JoinPath recognises as game-rooted.
    strSrc = "3DData/Control/Res/";
    strSrc += pTexture->m_szName;

    char szRect[48];
    _snprintf(szRect, sizeof(szRect), "%d %d %d %d", (int)pSprite->m_Rect.left,
        (int)pSprite->m_Rect.top, (int)(pSprite->m_Rect.right - pSprite->m_Rect.left),
        (int)(pSprite->m_Rect.bottom - pSprite->m_Rect.top));
    szRect[sizeof(szRect) - 1] = '\0';
    strRect = szRect;
    return true;
}

} // namespace RoseRmlIcons
