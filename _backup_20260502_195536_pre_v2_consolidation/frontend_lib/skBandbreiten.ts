// src/lib/skBandbreiten.ts
// Regionale Kurzschlussleistungs-Bandbreiten basierend auf PLZ-Bereichen

import type { Spannungsebene } from '@/types';

export interface SkBandbreite {
  min_mva: number;
  typ_mva: number;
  max_mva: number;
  region: string;
}

type RegionTyp = 'urban' | 'suburban' | 'rural';

const PLZ_REGION: Record<string, RegionTyp> = {
  '10':'urban','12':'urban','13':'urban','14':'suburban',
  '20':'urban','21':'suburban','22':'urban',
  '80':'urban','81':'urban','82':'suburban','83':'suburban',
  '40':'urban','41':'suburban','50':'urban','51':'suburban',
  '60':'urban','61':'suburban','63':'suburban','65':'suburban',
  '70':'urban','71':'suburban','72':'suburban','73':'suburban',
  '44':'urban','45':'urban','46':'urban','47':'urban',
  '30':'urban','31':'suburban','38':'suburban',
  '01':'urban','04':'urban',
  '90':'urban','91':'suburban',
  '28':'urban',
  '48':'suburban','49':'rural',
  '17':'rural','18':'rural','19':'rural','23':'rural','24':'rural',
  '25':'rural','26':'rural','27':'rural','29':'rural',
  '32':'rural','33':'rural','34':'rural','35':'rural','36':'rural','37':'rural',
  '39':'rural','54':'rural','55':'suburban','56':'rural',
  '57':'rural','58':'suburban','59':'rural',
  '66':'suburban','67':'suburban',
  '74':'rural','75':'rural','76':'suburban','77':'rural','78':'rural','79':'suburban',
  '84':'rural','85':'suburban','86':'suburban','87':'rural','88':'rural','89':'rural',
  '92':'rural','93':'rural','94':'rural','95':'rural','96':'rural','97':'rural','98':'rural','99':'rural',
  '02':'rural','03':'rural','06':'suburban','07':'rural','08':'rural','09':'rural',
  '15':'rural','16':'rural',
};

const SK_TABELLE: Record<RegionTyp, Record<Spannungsebene, SkBandbreite>> = {
  urban: {
    NS:  { min_mva: 8,    typ_mva: 15,   max_mva: 25,   region: 'Ballungsraum' },
    MS:  { min_mva: 200,  typ_mva: 350,  max_mva: 500,  region: 'Ballungsraum' },
    HS:  { min_mva: 2000, typ_mva: 3500, max_mva: 5000, region: 'Ballungsraum' },
  },
  suburban: {
    NS:  { min_mva: 5,    typ_mva: 10,   max_mva: 18,   region: 'Umland' },
    MS:  { min_mva: 120,  typ_mva: 250,  max_mva: 400,  region: 'Umland' },
    HS:  { min_mva: 1500, typ_mva: 2500, max_mva: 4000, region: 'Umland' },
  },
  rural: {
    NS:  { min_mva: 3,    typ_mva: 6,    max_mva: 12,   region: 'Laendlich' },
    MS:  { min_mva: 80,   typ_mva: 150,  max_mva: 250,  region: 'Laendlich' },
    HS:  { min_mva: 800,  typ_mva: 1500, max_mva: 2500, region: 'Laendlich' },
  },
};

function getRegion(plz: string): RegionTyp {
  const prefix = plz.substring(0, 2);
  return PLZ_REGION[prefix] ?? 'suburban';
}

export function getSkBandbreite(plz: string, se: Spannungsebene): SkBandbreite {
  return SK_TABELLE[getRegion(plz)][se];
}

export function getRegionTyp(plz: string): RegionTyp {
  return getRegion(plz);
}
