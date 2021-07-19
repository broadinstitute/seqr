import React from 'react'
import { Header, Table, List, Label } from 'semantic-ui-react'

const AcmgRuleSpecification = () => {
  return (
    <div>
      <Header>Rule Specification</Header>

      <Table celled structured padded>
        <Table.Body>
          <Table.Row>
            <Table.Cell textAlign="center">BA1</Table.Cell>
            <Table.Cell colSpan="2">
              <List bulleted>
                <List.Item key="rs_hcm_dcm_01">{'HCM/DCM: >= 0.1%'}</List.Item>
                <List.Item key="rs_noonan_005">{'Noonan: >= 0.05%'}</List.Item>
                <List.Item key="rs_default_06">{'Default: >= 0.6%'}</List.Item>
                <List.Item key="rs_autosomal_recessive_05">{'HL (Autosomal recessive): >= 0.5%'}</List.Item>
                <List.Item key="hl_autosomal_dominan_01">{'HL (Autosomal dominant): >= 0.1%'}</List.Item>
              </List>
            </Table.Cell>
          </Table.Row>

          <Table.Row>
            <Table.Cell textAlign="center">BS1</Table.Cell>
            <Table.Cell colSpan="2">
              <List bulleted>
                <List.Item key="rs_hcm_dcm_02">{'HCM/DCM: >= 0.2%'}</List.Item>
                <List.Item key="rs_noonan_0025">{'Noonan: >= 0.025%'}</List.Item>
                <List.Item key="rs_default_03">{'Default: >= 0.3%'}</List.Item>
                <List.Item key="rs_autosomal_recessive_03">{'HL (Autosomal recessive): >= 0.3%'}</List.Item>
                <List.Item key="hl_autosomal_dominan_02">{'HL (Autosomal dominant): >= 0.02%'}</List.Item>
              </List>
            </Table.Cell>
          </Table.Row>

          <Table.Row>
            <Table.Cell textAlign="center">BS1_P</Table.Cell>
            <Table.Cell colSpan="2">
              <List bulleted>
                <List.Item key="rs_autosomal_recessive_0703">HL (Autosomal recessive): 0.07-0.3%</List.Item>
              </List>
            </Table.Cell>
          </Table.Row>

          <Table.Row>
            <Table.Cell textAlign="center">PM2_P</Table.Cell>
            <Table.Cell colSpan="2">
              <List bulleted>
                <List.Item key="rs_autosomal_recessive_007">{'HL (Autosomal recessive): <= 0.007%'}</List.Item>
                <List.Item key="hl_autosomal_dominan_002">{'HL (Autosomal dominant): <= 0.002%'}</List.Item>
              </List>
            </Table.Cell>
          </Table.Row>

          <Table.Row>
            <Table.Cell textAlign="center">Proband Count (PS4)</Table.Cell>
            <Table.Cell>
              <Table>
                <Table.Body>
                  <Table.Row>
                    <Table.Cell>Noonan</Table.Cell>
                    <Table.Cell>#</Table.Cell>
                  </Table.Row>

                  <Table.Row>
                    <Table.Cell>Strong</Table.Cell>
                    <Table.Cell>5</Table.Cell>
                  </Table.Row>

                  <Table.Row>
                    <Table.Cell>Moderate</Table.Cell>
                    <Table.Cell>3</Table.Cell>
                  </Table.Row>

                  <Table.Row>
                    <Table.Cell>Supporting</Table.Cell>
                    <Table.Cell>1</Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>

            <Table.Cell>
              <Table>
                <Table.Body>
                  <Table.Row>
                    <Table.Cell>Cardio</Table.Cell>
                    <Table.Cell>#</Table.Cell>
                  </Table.Row>

                  <Table.Row>
                    <Table.Cell>Strong</Table.Cell>
                    <Table.Cell>15</Table.Cell>
                  </Table.Row>

                  <Table.Row>
                    <Table.Cell>Moderate</Table.Cell>
                    <Table.Cell>6</Table.Cell>
                  </Table.Row>

                  <Table.Row>
                    <Table.Cell>Supporting</Table.Cell>
                    <Table.Cell>2</Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
          </Table.Row>

          <Table.Row>
            <Table.Cell textAlign="center">In Trans (PM3)</Table.Cell>

            <Table.Cell>
              <Table>
                <Table.Body>
                  <Table.Row>
                    <Table.Cell>
                      <Label color="blue">Increase to PM3_Strong if observed in trans</Label>
                      <List bulleted>
                        <List.Item key="rs_2x_and_1_variant_path">{'2x and >= 1 variant in PATH'}</List.Item>
                        <List.Item key="rs_3x_other_variants_lp">3x if other variants are LP</List.Item>
                      </List>
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>

            <Table.Cell>
              <Table>
                <Table.Body>
                  <Table.Row>
                    <Table.Cell>
                      <Label color="blue">Increase to VeryStrong if observed in trans</Label>
                      <List bulleted>
                        <List.Item key="rs_4x_and_2_variant_path">{'4x and >= 2 variant in PATH (can be same variant)'}</List.Item>
                        <List.Item key="rs_4x_lpp_different">4x if LP/P variants are all different</List.Item>
                      </List>
                    </Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
          </Table.Row>

          <Table.Row>
            <Table.Cell textAlign="center">BP7</Table.Cell>
            <Table.Cell colSpan="2">Nonconserved splice is for variants at positions: -4, +7 to +15<br />AND<br />{'-5 to -15 positions with changes >T or >C'}</Table.Cell>
          </Table.Row>

          <Table.Row>
            <Table.Cell textAlign="center">PP1 (Hearing loss)</Table.Cell>
            <Table.Cell colSpan="2">
              <Table color="blue">
                <Table.Header>
                  <Table.Row>
                    <Table.HeaderCell rowSpan="2"></Table.HeaderCell>
                    <Table.HeaderCell colSpan="3" textAlign="center">General Recommendations (Phenocopy not an issue)</Table.HeaderCell>
                  </Table.Row>
                </Table.Header>

                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell></Table.Cell>
                    <Table.Cell>Supporting</Table.Cell>
                    <Table.Cell>Moderate</Table.Cell>
                    <Table.Cell>Strong</Table.Cell>
                  </Table.Row>

                  <Table.Row textAlign="center">
                    <Table.Cell>Likelihood</Table.Cell>
                    <Table.Cell>4:1</Table.Cell>
                    <Table.Cell>16:1</Table.Cell>
                    <Table.Cell>32:1</Table.Cell>
                  </Table.Row>

                  <Table.Row textAlign="center">
                    <Table.Cell>LOD Score</Table.Cell>
                    <Table.Cell>0.6</Table.Cell>
                    <Table.Cell>1.2</Table.Cell>
                    <Table.Cell>1.5</Table.Cell>
                  </Table.Row>

                  <Table.Row textAlign="center">
                    <Table.Cell>Autosomal dominant threshold</Table.Cell>
                    <Table.Cell>2 affected segregations</Table.Cell>
                    <Table.Cell>4 affected segregations</Table.Cell>
                    <Table.Cell>5 affected segregations</Table.Cell>
                  </Table.Row>

                  <Table.Row textAlign="center">
                    <Table.Cell>Autosomal recessive threshold</Table.Cell>
                    <Table.Cell>See Table 2</Table.Cell>
                    <Table.Cell>See Table 2</Table.Cell>
                    <Table.Cell>See Table 2</Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
          </Table.Row>

          <Table.Row>
            <Table.Cell textAlign="center">Affected Segregations</Table.Cell>
            <Table.Cell colSpan="2">
              <Table color="blue">
                <Table.Header>
                  <Table.Row textAlign="center">
                    <Table.HeaderCell colSpan="12">General Recommendations (Phenocopy not an issue)</Table.HeaderCell>
                  </Table.Row>

                  <Table.Row textAlign="center">
                    <Table.HeaderCell colSpan="12">Unaffected Segregations</Table.HeaderCell>
                  </Table.Row>
                </Table.Header>

                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell></Table.Cell>
                    {(Array.from(Array(11).keys())).map(number => <Table.Cell>{number}</Table.Cell>)}
                  </Table.Row>

                  <Table.Row textAlign="center">
                    <Table.Cell>0</Table.Cell>
                    <Table.Cell>0</Table.Cell>
                    <Table.Cell>0.12</Table.Cell>
                    <Table.Cell>0.25</Table.Cell>
                    <Table.Cell>0.37</Table.Cell>
                    <Table.Cell>0.5</Table.Cell>
                    <Table.Cell>0.62</Table.Cell>
                    <Table.Cell>0.75</Table.Cell>
                    <Table.Cell>0.87</Table.Cell>
                    <Table.Cell>1</Table.Cell>
                    <Table.Cell>1.12</Table.Cell>
                    <Table.Cell>1.25</Table.Cell>
                  </Table.Row>

                  <Table.Row textAlign="center">
                    <Table.Cell>1</Table.Cell>
                    <Table.Cell>0.6</Table.Cell>
                    <Table.Cell>0.73</Table.Cell>
                    <Table.Cell>0.85</Table.Cell>
                    <Table.Cell>0.98</Table.Cell>
                    <Table.Cell>1.1</Table.Cell>
                    <Table.Cell>1.23</Table.Cell>
                    <Table.Cell>1.35</Table.Cell>
                    <Table.Cell>1.48</Table.Cell>
                    <Table.Cell>1.6</Table.Cell>
                    <Table.Cell>1.73</Table.Cell>
                    <Table.Cell>1.85</Table.Cell>
                  </Table.Row>

                  <Table.Row textAlign="center">
                    <Table.Cell>2</Table.Cell>
                    <Table.Cell>1.2</Table.Cell>
                    <Table.Cell>1.33</Table.Cell>
                    <Table.Cell>1.45</Table.Cell>
                    <Table.Cell>1.58</Table.Cell>
                    <Table.Cell>1.7</Table.Cell>
                    <Table.Cell>1.83</Table.Cell>
                    <Table.Cell>1.95</Table.Cell>
                    <Table.Cell>2.08</Table.Cell>
                    <Table.Cell>2.2</Table.Cell>
                    <Table.Cell>2.33</Table.Cell>
                    <Table.Cell>2.45</Table.Cell>
                  </Table.Row>

                  <Table.Row textAlign="center">
                    <Table.Cell>3</Table.Cell>
                    <Table.Cell>1.81</Table.Cell>
                    <Table.Cell>1.93</Table.Cell>
                    <Table.Cell>2.06</Table.Cell>
                    <Table.Cell>2.18</Table.Cell>
                    <Table.Cell>2.31</Table.Cell>
                    <Table.Cell>2.43</Table.Cell>
                    <Table.Cell>2.56</Table.Cell>
                    <Table.Cell>2.68</Table.Cell>
                    <Table.Cell>2.81</Table.Cell>
                    <Table.Cell>2.93</Table.Cell>
                    <Table.Cell>3.06</Table.Cell>
                  </Table.Row>

                  <Table.Row textAlign="center">
                    <Table.Cell>4</Table.Cell>
                    <Table.Cell>2.41</Table.Cell>
                    <Table.Cell>2.53</Table.Cell>
                    <Table.Cell>2.66</Table.Cell>
                    <Table.Cell>2.78</Table.Cell>
                    <Table.Cell>2.91</Table.Cell>
                    <Table.Cell>3.03</Table.Cell>
                    <Table.Cell>3.16</Table.Cell>
                    <Table.Cell>3.28</Table.Cell>
                    <Table.Cell>3.41</Table.Cell>
                    <Table.Cell>3.53</Table.Cell>
                    <Table.Cell>3.66</Table.Cell>
                  </Table.Row>

                  <Table.Row textAlign="center">
                    <Table.Cell>5</Table.Cell>
                    <Table.Cell>3.01</Table.Cell>
                    <Table.Cell>3.14</Table.Cell>
                    <Table.Cell>3.26</Table.Cell>
                    <Table.Cell>3.39</Table.Cell>
                    <Table.Cell>3.51</Table.Cell>
                    <Table.Cell>3.63</Table.Cell>
                    <Table.Cell>3.76</Table.Cell>
                    <Table.Cell>3.88</Table.Cell>
                    <Table.Cell>4.01</Table.Cell>
                    <Table.Cell>4.13</Table.Cell>
                    <Table.Cell>4.26</Table.Cell>
                  </Table.Row>

                  <Table.Row textAlign="center">
                    <Table.Cell>6</Table.Cell>
                    <Table.Cell>3.61</Table.Cell>
                    <Table.Cell>3.74</Table.Cell>
                    <Table.Cell>3.86</Table.Cell>
                    <Table.Cell>3.99</Table.Cell>
                    <Table.Cell>4.11</Table.Cell>
                    <Table.Cell>4.24</Table.Cell>
                    <Table.Cell>4.36</Table.Cell>
                    <Table.Cell>4.49</Table.Cell>
                    <Table.Cell>4.61</Table.Cell>
                    <Table.Cell>4.74</Table.Cell>
                    <Table.Cell>4.86</Table.Cell>
                  </Table.Row>

                  <Table.Row textAlign="center">
                    <Table.Cell>7</Table.Cell>
                    <Table.Cell>4.21</Table.Cell>
                    <Table.Cell>4.34</Table.Cell>
                    <Table.Cell>4.46</Table.Cell>
                    <Table.Cell>4.59</Table.Cell>
                    <Table.Cell>4.71</Table.Cell>
                    <Table.Cell>4.84</Table.Cell>
                    <Table.Cell>4.96</Table.Cell>
                    <Table.Cell>5.09</Table.Cell>
                    <Table.Cell>5.21</Table.Cell>
                    <Table.Cell>5.34</Table.Cell>
                    <Table.Cell>5.46</Table.Cell>
                  </Table.Row>

                  <Table.Row textAlign="center">
                    <Table.Cell>8</Table.Cell>
                    <Table.Cell>4.82</Table.Cell>
                    <Table.Cell>4.94</Table.Cell>
                    <Table.Cell>5.07</Table.Cell>
                    <Table.Cell>5.19</Table.Cell>
                    <Table.Cell>5.32</Table.Cell>
                    <Table.Cell>5.44</Table.Cell>
                    <Table.Cell>5.57</Table.Cell>
                    <Table.Cell>5.69</Table.Cell>
                    <Table.Cell>5.82</Table.Cell>
                    <Table.Cell>5.94</Table.Cell>
                    <Table.Cell>6.07</Table.Cell>
                  </Table.Row>

                  <Table.Row textAlign="center">
                    <Table.Cell>9</Table.Cell>
                    <Table.Cell>5.42</Table.Cell>
                    <Table.Cell>5.54</Table.Cell>
                    <Table.Cell>5.67</Table.Cell>
                    <Table.Cell>5.79</Table.Cell>
                    <Table.Cell>5.92</Table.Cell>
                    <Table.Cell>6.04</Table.Cell>
                    <Table.Cell>6.17</Table.Cell>
                    <Table.Cell>6.29</Table.Cell>
                    <Table.Cell>6.42</Table.Cell>
                    <Table.Cell>6.54</Table.Cell>
                    <Table.Cell>6.67</Table.Cell>
                  </Table.Row>

                  <Table.Row textAlign="center">
                    <Table.Cell>10</Table.Cell>
                    <Table.Cell>6.02</Table.Cell>
                    <Table.Cell>6.15</Table.Cell>
                    <Table.Cell>6.27</Table.Cell>
                    <Table.Cell>6.4</Table.Cell>
                    <Table.Cell>6.52</Table.Cell>
                    <Table.Cell>6.65</Table.Cell>
                    <Table.Cell>6.77</Table.Cell>
                    <Table.Cell>6.9</Table.Cell>
                    <Table.Cell>7.02</Table.Cell>
                    <Table.Cell>7.15</Table.Cell>
                    <Table.Cell>7.27</Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
          </Table.Row>

          <Table.Row>
            <Table.Cell textAlign="center">PM3 (Hearing Loss)</Table.Cell>
            <Table.Cell colSpan="2">
              <Table color="blue">
                <Table.Header>
                  <Table.Row textAlign="center">
                    <Table.HeaderCell>Classification/zygosity of other variant</Table.HeaderCell>
                    <Table.HeaderCell>Known in trans</Table.HeaderCell>
                    <Table.HeaderCell>Phase unknown</Table.HeaderCell>
                  </Table.Row>
                </Table.Header>

                <Table.Body>
                  <Table.Row textAlign="center">
                    <Table.Cell>Pathogenic/Likely pathogenic</Table.Cell>
                    <Table.Cell>1.0</Table.Cell>
                    <Table.Cell>0.5</Table.Cell>
                  </Table.Row>

                  <Table.Row textAlign="center">
                    <Table.Cell>Homozygous occurrence (Max points from homozygotes 1)</Table.Cell>
                    <Table.Cell>0.5</Table.Cell>
                    <Table.Cell>N/A</Table.Cell>
                  </Table.Row>

                  <Table.Row textAlign="center">
                    <Table.Cell>Homozygous occurrence due to consanguinity, rare uncertain significance<br />(confirmed in trans) (Max point 0.5)</Table.Cell>
                    <Table.Cell>0.25</Table.Cell>
                    <Table.Cell>0</Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
          </Table.Row>

          <Table.Row>
            <Table.Cell textAlign="center">Disease-based Criteria Specifications- curated by ClinGen</Table.Cell>
            <Table.Cell colSpan="2">
              <Table>
                <Table.Body>
                  <Table.Row>
                    <Table.Cell>
                      <List bulleted>
                        <List.Item key="cardiomyopathy">Cardiomyopathy: <a href="https://cspec.genome.network/cspec/ui/svi/svi/GN002" target="_blank">https://cspec.genome.network/cspec/ui/svi/svi/GN002</a></List.Item>
                        <List.Item key="rasopathy">RASopathy: <a href="https://cspec.genome.network/cspec/ui/svi/svi/GN004" target="_blank">https://cspec.genome.network/cspec/ui/svi/svi/GN004</a></List.Item>
                        <List.Item key="hearing-loss">Hearing Loss: <a href="https://cspec.genome.network/cspec/ui/svi/svi/GN005" target="_blank">https://cspec.genome.network/cspec/ui/svi/svi/GN005</a></List.Item>
                        <List.Item key="rett-angelman-disorders">Rett and Angelman-like Disorders: <a href="https://cspec.genome.network/cspec/ui/svi/svi/GN016" target="_blank">https://cspec.genome.network/cspec/ui/svi/svi/GN016</a></List.Item>
                        <List.Item key="mitochondrial-disease-mitochondrial">Mitochondrial Disease Mitochondrial: <a href="https://cspec.genome.network/cspec/ui/svi/svi/GN015" target="_blank">https://cspec.genome.network/cspec/ui/svi/svi/GN015</a></List.Item>
                        <List.Item key="mitochondrial-disease-nuclear">Mitochondrial Disease Nuclear: <a href="https://cspec.genome.network/cspec/ui/svi/svi/GN014" target="_blank">https://cspec.genome.network/cspec/ui/svi/svi/GN014</a></List.Item>
                        <List.Item key="hypercholesterolemia:">Hypercholesterolemia: <a href="https://cspec.genome.network/cspec/ui/svi/svi/GN013" target="_blank">https://cspec.genome.network/cspec/ui/svi/svi/GN013</a></List.Item>
                        <List.Item key="hyperthermia-susceptibility">Hyperthermia Susceptibility: <a href="https://cspec.genome.network/cspec/ui/svi/svi/GN012" target="_blank">https://cspec.genome.network/cspec/ui/svi/svi/GN012</a></List.Item>
                        <List.Item key="platelet-discorders">Platelet Disorders: <a href="https://cspec.genome.network/cspec/ui/svi/svi/GN011" target="_blank">https://cspec.genome.network/cspec/ui/svi/svi/GN011</a></List.Item>
                        <List.Item key="lysosmal-storage-disorders">Lysosomal Storage Disorders: <a href="https://cspec.genome.network/cspec/ui/svi/svi/GN010" target="_blank">https://cspec.genome.network/cspec/ui/svi/svi/GN010</a></List.Item>
                        <List.Item key="pten">PTEN: <a href="https://cspec.genome.network/cspec/ui/svi/svi/GN003" target="_blank">https://cspec.genome.network/cspec/ui/svi/svi/GN003</a></List.Item>
                        <List.Item key="myeloid-malignancy">Myeloid Malignancy: <a href="https://cspec.genome.network/cspec/ui/svi/svi/GN008" target="_blank">https://cspec.genome.network/cspec/ui/svi/svi/GN008</a></List.Item>
                        <List.Item key="cdh1">CDH1: <a href="https://cspec.genome.network/cspec/ui/svi/svi/GN007" target="_blank">https://cspec.genome.network/cspec/ui/svi/svi/GN007</a></List.Item>
                        <List.Item key="tps3">TPS3: <a href="https://cspec.genome.network/cspec/ui/svi/svi/GN009" target="_blank">https://cspec.genome.network/cspec/ui/svi/svi/GN009</a></List.Item>
                        <List.Item key="pah">PAH: <a href="https://cspec.genome.network/cspec/ui/svi/svi/GN006" target="_blank">https://cspec.genome.network/cspec/ui/svi/svi/GN006</a></List.Item>
                      </List>
                    </Table.Cell>
                  </Table.Row>

                  <Table.Row>
                    <Table.Cell>ClinGen Registry: <a href="https://cspec.genome.network/cspec/ui/svi/" target="_blank">https://cspec.genome.network/cspec/ui/svi/</a></Table.Cell>
                  </Table.Row>
                </Table.Body>
              </Table>
            </Table.Cell>
          </Table.Row>

          <Table.Row>
            <Table.Cell colSpan="3">
              <Table color="blue">
                <Table.Header>
                  <Table.HeaderCell textAlign="center"></Table.HeaderCell>
                  <Table.HeaderCell textAlign="center">Comp Het Only</Table.HeaderCell>
                  <Table.HeaderCell textAlign="center">Hom only</Table.HeaderCell>
                  <Table.HeaderCell textAlign="center">Comp Het + Hom</Table.HeaderCell>
                </Table.Header>

                <Table.Row textAlign="center">
                  <Table.Cell>Supporting (PM3_Supporting) (total 0.5 points)</Table.Cell>
                  <Table.Cell>1 observation with LP/P but phase unknown or 2 VUS co-occurrences (exception: large genes)</Table.Cell>
                  <Table.Cell>1 with ADO rules out</Table.Cell>
                  <Table.Cell>N/A</Table.Cell>
                </Table.Row>

                <Table.Row textAlign="center">
                  <Table.Cell>Moderate (PM3) (total 1.0 points)</Table.Cell>
                  <Table.Cell>1 comp het  with LP/P 2 observations with different LP/P but phase unknown</Table.Cell>
                  <Table.Cell>2 difference families and use of exome data to rule out consanguinity</Table.Cell>
                  <Table.Cell textAlign="left">
                    A combination of the following adding to 1 point:
                    <List bulleted>
                      <List.Item key="rs_observations_with_lpp">Observations with LP/P but phase unknown</List.Item>
                      <List.Item key="rs_compund_rare_vus">Compound het with rare VUS</List.Item>
                      <List.Item key="rs_hom_ado_rules_out">Hom w/ ADO rules out</List.Item>
                    </List>
                  </Table.Cell>
                </Table.Row>

                <Table.Row textAlign="center">
                  <Table.Cell>Strong (PM3_Strong) (total 2.0 points)</Table.Cell>
                  <Table.Cell>2 comp het</Table.Cell>
                  <Table.Cell>N/A</Table.Cell>
                  <Table.Cell textAlign="left">
                    A combination of the following adding to 2 points:
                    <List bulleted>
                      <List.Item key="rs_comp_lpp">Comp het with LP/P</List.Item>
                      <List.Item key="rs_hom_ado_rules_out_2">Hom w/ ADO rules out</List.Item>
                      <List.Item key="rs_observations_lpp_phase_unknown">Observations with different LP/P but phase unknown</List.Item>
                      <List.Item key="rs_compund_rare_vus_2">Compund het with rare VUS</List.Item>
                    </List>
                  </Table.Cell>
                </Table.Row>

                <Table.Row textAlign="center">
                  <Table.Cell>Very Strong (PM3_VeryStrong) (total 4.0 points)</Table.Cell>
                  <Table.Cell>4 comp het</Table.Cell>
                  <Table.Cell>N/A</Table.Cell>
                  <Table.Cell textAlign="left">
                    A combination of the following adding to 4 points:
                    <List bulleted>
                      <List.Item key="rs_comp_lpp_2">Comp hets with LP/P</List.Item>
                      <List.Item key="rs_different_observations_lpp_phase_unknown">Different observations with LP/P but phase unknown</List.Item>
                      <List.Item key="rs_compund_rare_vus_3">Compound het with rare VUS</List.Item>
                      <List.Item key="rs_hom_ado_rules_out_3">How w/ ADO ruled out</List.Item>
                    </List>
                  </Table.Cell>
                </Table.Row>
              </Table>
            </Table.Cell>
          </Table.Row>
        </Table.Body>
      </Table>
    </div>
  )
}

export default AcmgRuleSpecification
