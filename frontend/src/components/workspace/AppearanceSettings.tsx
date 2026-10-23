import { Check, Monitor, Moon, Sun } from 'lucide-react';
import { useTheme } from '../ThemeProvider';
import { COLOR_PALETTES } from '../../utils/theme';

const choices = [
  { value: 'light', label: 'Light', icon: Sun, detail: 'Warm cream with soft ivory surfaces.' },
  { value: 'dark', label: 'Dark', icon: Moon, detail: 'Deep charcoal for low light.' },
  { value: 'system', label: 'System', icon: Monitor, detail: 'Follow your device appearance.' },
] as const;

export function AppearanceSettings() {
  const { preference, setPreference, palette, setPalette } = useTheme();
  return <section className="space-y-5">
    <div><h3 className="text-sm font-semibold text-ink">Appearance</h3>
      <p className="text-sm text-muted mt-2">Choose how MeetPilot looks. This preference is saved in this browser across your workspaces.</p></div>
    <fieldset className="mp-theme-choices"><legend className="sr-only">Color theme</legend>
      {choices.map(choice => <label key={choice.value} className={`mp-theme-choice ${preference === choice.value ? 'is-selected' : ''}`}>
        <input type="radio" name="color-theme" value={choice.value} checked={preference === choice.value} aria-label={choice.label} aria-describedby={`theme-description-${choice.value}`}
          onChange={() => setPreference(choice.value)} />
        <choice.icon size={22} aria-hidden="true" /><strong>{choice.label}</strong><small id={`theme-description-${choice.value}`}>{choice.detail}</small>
      </label>)}
    </fieldset>
    <div className="pt-5 border-t border-line">
      <h4 className="text-sm font-semibold text-ink">Color palette</h4>
      <p className="text-sm text-muted mt-2">Select a palette to preview it across MeetPilot immediately. Each works in light and dark mode.</p>
    </div>
    <fieldset className="mp-palette-choices"><legend className="sr-only">Color palette</legend>
      {COLOR_PALETTES.map(choice => <label key={choice.id} className={`mp-palette-choice ${palette === choice.id ? 'is-selected' : ''}`}>
        <input type="radio" name="color-palette" value={choice.id} checked={palette === choice.id} aria-label={choice.label}
          aria-describedby={`palette-description-${choice.id}`} onChange={() => setPalette(choice.id)} />
        <span className="mp-palette-swatches" aria-hidden="true">{choice.swatches.map(color => <span key={color} style={{ backgroundColor: color }} />)}</span>
        <span className="mp-palette-label"><strong>{choice.label}</strong>{palette === choice.id && <Check size={16} aria-hidden="true" />}</span>
        <small id={`palette-description-${choice.id}`}>{choice.description}</small>
      </label>)}
    </fieldset>
  </section>;
}
