#include "stdafx.h"

#include "RoseRmlLayout.h"

#include <RmlUi/Core/Element.h>
#include <RmlUi/Core/Event.h>
#include <RmlUi/Core/EventListener.h>

#include "rose/common/log.h"

#include <stdio.h>
#include <string>

namespace {

const char* kIniPath = ".\\rose-next.ini";
const char* kSection = "UI_LAYOUT";

void
SetPosition(Rml::Element* pPanel, float x, float y) {
    pPanel->SetProperty(Rml::PropertyId::Left, Rml::Property(x, Rml::Unit::PX));
    pPanel->SetProperty(Rml::PropertyId::Top, Rml::Property(y, Rml::Unit::PX));
}

/// Saves the panel's position when a drag inside it ends. dragend is
/// dispatched to the handle and bubbles, so listening on the panel catches a
/// handle anywhere inside it. Owned by the element: deletes itself on detach.
class SaveOnDragEnd: public Rml::EventListener {
public:
    explicit SaveOnDragEnd(const char* pszKey): m_strKey(pszKey) {}

    void ProcessEvent(Rml::Event& ev) override {
        Rml::Element* pPanel = ev.GetCurrentElement();
        if (pPanel == NULL)
            return;

        const Rml::Vector2f pos = pPanel->GetAbsoluteOffset(Rml::BoxArea::Border);
        char szBuf[32];
        _snprintf(szBuf, sizeof(szBuf), "%d,%d", (int)pos.x, (int)pos.y);
        szBuf[sizeof(szBuf) - 1] = '\0';
        WritePrivateProfileStringA(kSection, m_strKey.c_str(), szBuf, kIniPath);
    }

    void OnDetach(Rml::Element*) override { delete this; }

private:
    std::string m_strKey;
};

} // namespace

namespace RoseRmlLayout {

void
Track(Rml::Element* pPanel, const char* pszKey) {
    if (pPanel == NULL || pszKey == NULL)
        return;

    char szBuf[32] = {0};
    GetPrivateProfileStringA(kSection, pszKey, "", szBuf, sizeof(szBuf), kIniPath);
    int x = 0, y = 0;
    if (szBuf[0] != '\0' && sscanf(szBuf, "%d,%d", &x, &y) == 2)
        SetPosition(pPanel, (float)x, (float)y);

    pPanel->AddEventListener(Rml::EventId::Dragend, new SaveOnDragEnd(pszKey));
}

void
Clamp(Rml::Element* pPanel, int iViewportW, int iViewportH) {
    if (pPanel == NULL)
        return;

    /// Zero until the first layout; nothing to clamp against yet.
    const Rml::Vector2f size = pPanel->GetBox().GetSize(Rml::BoxArea::Border);
    if (size.x <= 0.0f || size.y <= 0.0f)
        return;

    const Rml::Vector2f pos = pPanel->GetAbsoluteOffset(Rml::BoxArea::Border);
    const float fMaxX = max(0.0f, (float)iViewportW - size.x);
    const float fMaxY = max(0.0f, (float)iViewportH - size.y);

    float x = pos.x;
    float y = pos.y;
    if (x < 0.0f)
        x = 0.0f;
    if (x > fMaxX)
        x = fMaxX;
    if (y < 0.0f)
        y = 0.0f;
    if (y > fMaxY)
        y = fMaxY;

    if (x != pos.x || y != pos.y)
        SetPosition(pPanel, x, y);
}

} // namespace RoseRmlLayout
