/* eslint-disable react/jsx-one-expression-per-line */

import PropTypes from 'prop-types'
import React from 'react'
import { Header, Segment, List, Icon } from 'semantic-ui-react'

import { WORKSPACE_REQUIREMENTS } from 'shared/components/panel/LoadWorkspaceDataForm'
import { ActiveDisabledNavLink } from 'shared/components/StyledComponents'
import { VCF_DOCUMENTATION_URL } from 'shared/utils/constants'
import { SeqrAvailability } from './LandingPage'

const ENGLISH = 'en'
const SPANISH = 'es'

const FAQS = [
  {
    [ENGLISH]: {
      header: 'Q. What is seqr?',
      content: (
        <div>
          seqr is an open source, Federal Information Security Management Act (FISMA) compliant genomic data analysis
          platform for rare disease diagnosis and gene discovery. The variant search interface is designed for
          family-based analyses. The seqr platform can load a joint called VCF and annotate it with relevant information
          for Mendelian analysis in a user-friendly web interface with links to external resources. Users can perform
          de novo/dominant, recessive (homozygous/compound heterozygous/X-linked), or custom searches (gene lists,
          incomplete penetrance, etc.) within a family to efficiently identify a diagnostic or candidate cause of
          disease
          among single nucleotide variants and indels. The platform supports searching a gene list across a group of
          samples. Through the Matchmaker Exchange interface, seqr also supports submission of candidate variants/genes
          and phenotypic information to an international network for gene discovery. <br /><br />

          To preview the functionality available in the seqr platform, please see our &nbsp;
          <a href="https://youtube.com/playlist?list=PLlMMtlgw6qNiY6mkBu111-lpmANKHdGKM" target="_blank" rel="noreferrer">
            tutorial videos
          </a>.
        </div>
      ),
    },
    [SPANISH]: {
      header: 'P. ¿Qué es seqr?',
      content: (
        <div>
          seqr es una plataforma open source de análisis de datos genómicos compatible con la Federal Information
          Security Management Act (FISMA, por sus siglas en inglés) para el diagnóstico de enfermedades raras y el
          descubrimiento de genes. La interfaz de búsqueda de variantes está diseñada para análisis basados en familias.
          La plataforma seqr puede cargar un joint, o conjunto, denominado VCF y anotarlo con información relevante para
          el análisis mendeliano en una interfaz web fácil de usar con enlaces a recursos externos. Los usuarios pueden
          realizar búsquedas de novo/dominante, recesivas (homocigotos/heterocigotos compuestos/ligados al cromosoma X)
          o personalizadas (listas de genes, penetrancia incompleta, etc.) dentro de una familia para identificar de
          manera eficiente un diagnóstico o una causa candidata de enfermedad entre las variantes de un solo nucleótido
          e indeles. La plataforma admite la búsqueda de una lista de genes en un grupo de muestras. A través de la
          interfaz Matchmaker Exchange, seqr también admite el envío de variantes/genes candidatos e información
          fenotípica a una red internacional para el descubrimiento de genes. <br /><br />

          Para revisar la funcionalidad disponible en la plataforma seqr, consulte nuestros &nbsp;
          <a href="https://youtube.com/playlist?list=PLlMMtlgw6qNiY6mkBu111-lpmANKHdGKM" target="_blank" rel="noreferrer">
            videos tutoriales
          </a>.
        </div>
      ),
    },
  }, {
    [ENGLISH]: {
      header: 'Q. What analyses are not supported in seqr?',
      content: (
        <List bulleted>
          <List.Item>
            seqr is not designed for cohort or gene burden analyses. You can search for variants in a candidate gene
            across your data but seqr will not provide a quantification of how much variation you should expect to see.
          </List.Item>
          <List.Item>
            seqr is not an annotation pipeline for a VCF. While annotations are added when data is loaded in seqr, you
            cannot output the annotated VCF from seqr.
          </List.Item>
          <List.Item>
            seqr does not have reporting capabilities, although there is limited support for downloading short variant
            lists from seqr that could be used as input to generate a report externally.
          </List.Item>
        </List>
      ),
    },
    [SPANISH]: {
      header: 'P. ¿Qué tipos de análisis no admite seqr?',
      content: (
        <List bulleted>
          <List.Item>
            seqr no está diseñado para análisis de carga génica o de cohortes. Puede buscar variantes en un gen
            candidato a través de sus datos, pero seqr no proporcionará una cuantificación de cuánta variación debe
            esperar ver.
          </List.Item>
          <List.Item>
            seqr no es un canal de anotación para un VCF. Aunque las anotaciones se agregan cuando los datos se cargan
            en seqr, no se puede generar el VCF anotado de seqr.
          </List.Item>
          <List.Item>
            seqr no tiene capacidades de generación de informes, aunque existe un soporte limitado para descargar listas
            de variantes cortas de seqr que podrían usarse como entrada para generar un informe externo.
          </List.Item>
        </List>
      ),
    },
  }, {
    [ENGLISH]: {
      header: 'Q. Can I try out seqr?',
      content: (
        <div>
          Yes! Please create a seqr account and test out basic functionality using the demonstration project.
          <br /><br />

          The seqr login process requires that you register your email address in the NHGRI&quot;s Genomic Data Science
          Analysis, Visualization, and Informatics Lab-Space (AnVIL*). This requires a Google account, either a Gmail
          account or registering your non-Gmail email account with Google. <br /><br />

          Instructions to register using Gmail accounts or Google-registered email account:
          <List ordered>
            <List.Item>
              Go to <a href="https://anvil.terra.bio" target="_blank" rel="noreferrer">https://anvil.terra.bio</a>
            </List.Item>
            <List.Item>
              Open the hamburger menu ( <Icon name="bars" />) at the top left and click &quot;Sign In With Google&quot;.
              Sign in using the Gmail or Google-registered* email address you plan to use to log in to seqr
            </List.Item>
            <List.Item>
              You will be prompted to register and accept the AnVIL terms of service
            </List.Item>
            <List.Item>
              Go to <a href="https://seqr.broadinstitute.org" target="_blank" rel="noreferrer">https://seqr.broadinstitute.org</a>
              &nbsp; and confirm that you can log in. seqr will display a demo project that you are welcome to play
              around with to test how it works
            </List.Item>
          </List>

          *If you would prefer to use your institutional or other non-Gmail email address, you can follow &nbsp;
          <a href="https://anvilproject.org/learn/account-setup/obtaining-a-google-id" target="_blank" rel="noreferrer">this link</a>
          &nbsp; for instructions on how to create an account that is associated with your non-Gmail, institutional
          email address, then proceed with the instructions above.
        </div>
      ),
    },
    [SPANISH]: {
      header: 'P. ¿Puedo probar seqr?',
      content: (
        <div>
          ¡Sí! Cree una cuenta de seqr y pruebe la funcionalidad básica utilizando el proyecto de demostración.
          <br /><br />

          El proceso de inicio de sesión de seqr requiere que registre su dirección de correo electrónico en el Genomic
          Data Science Analysis, Visualization, and Informatics Lab-Space (AnVIL*) del NHGRI. Esto requiere una cuenta
          de Google, ya sea una cuenta de Gmail o registrar su cuenta de correo electrónico que no sea de Gmail con
          Google.<br /><br />

          Instrucciones para registrarse usando cuentas de Gmail o una cuenta de correo electrónico registrada con
          Google:
          <List ordered>
            <List.Item>
              Vaya a <a href="https://anvil.terra.bio" target="_blank" rel="noreferrer">https://anvil.terra.bio</a>
            </List.Item>
            <List.Item>
              Abra el menu ( <Icon name="bars" />) en la parte superior izquierda y haz clic en &quot;Iniciar sesión con
              Google&quot;. nicie sesión con la dirección de correo electrónico registrada con Gmail o Google* que
              planea usar para iniciar sesión en seqr.
            </List.Item>
            <List.Item>
              Se le pedirá que se registre y acepte los términos de servicio de AnVIL.
            </List.Item>
            <List.Item>
              Vaya a <a href="https://seqr.broadinstitute.org" target="_blank" rel="noreferrer">https://seqr.broadinstitute.org</a>
              &nbsp; y confirme que puede iniciar sesión. seqr mostrará un proyecto de demostración con el que se puede
              jugar para probar cómo funciona.
            </List.Item>
          </List>

          *Si prefiere usar su dirección de correo electrónico institucional u otra que no sea de Gmail, puede seguir
          &nbsp;<a href="https://anvilproject.org/learn/account-setup/obtaining-a-google-id" target="_blank" rel="noreferrer">este enlace</a>
          &nbsp;para obtener instrucciones sobre cómo crear una cuenta que esté asociada con su dirección de correo
          electrónico institucional que no sea de Gmail, luego continúe con las instrucciones anteriores.
        </div>
      ),
    },
  }, {
    [ENGLISH]: {
      header: 'Q. How can I analyze my data in seqr?',
      content: (
        <div>
          There are 3 mechanisms through which you can load and analyze your data in seqr:
          <SeqrAvailability hasFootnote />

          *AnVIL is a controlled-access NIH-designated data repository supported on the Terra platform. Users are
          expected
          to ensure that data use and sharing within a Terra or AnVIL Workspace are conducted in accordance with all
          applicable national, tribal, and state laws and regulations, as well as relevant institutional policies and
          procedures for handling genomic data. However, because seqr runs within Terra or AnVIL workspaces, no
          additional
          regulatory approval is required to use seqr to analyze data stored on Terra or AnVIL. <br />

          To learn more about generating a joint called vcf, please refer to this &nbsp;
          <a href={VCF_DOCUMENTATION_URL} target="_blank" rel="noreferrer">
            documentation
          </a>
        </div>
      ),
    },
    [SPANISH]: {
      header: 'P. ¿Cómo puedo analizar mis datos en seqr?',
      content: (
        <div>
          Hay 3 mecanismos a través de los cuales puede cargar y analizar sus datos en seqr:
          <List ordered>
            <List.Item>
              A través de la <a href="https://anvilproject.org" target="_blank" rel="noreferrer">AnVIL platform</a>*
              donde se pueden realizar solicitudes de carga de un conjunto denominado vcf en seqr. Para obtener más
              información sobre cómo generar un conjunto denominado vcf, consulte el&nbsp;
              <a href="https://www.youtube.com/watch?v=TvYz_VI9vN0&ab_channel=BroadInstitute" target="_blank" rel="noreferrer">vídeo tutorial</a>
            </List.Item>
            <List.Item>
              Como colaborador proporcionando muestras para secuenciación dentro del &nbsp;
              <a href="https://cmg.broadinstitute.org" target="_blank" rel="noreferrer">Broad Institute Center for Mendelian Genomics</a>,
              parte del <a href="https://gregorconsortium.org" target="_blank" rel="noreferrer">consorcio GREGoR</a>
            </List.Item>
            <List.Item>
              En GitHub como &nbsp;
              <a href="http://github.com/broadinstitute/seqr" target="_blank" rel="noreferrer">proyecto de open source</a>
              &nbsp;para descarga e instalación local
            </List.Item>
          </List>

          *AnVIL es un repositorio de datos designado por el NIH de acceso controlado compatible con la plataforma
          Terra. Se espera que los usuarios se aseguren de que el uso y el intercambio de datos dentro de Terra o AnVIL
          Workspace se lleven a cabo de acuerdo con todas las leyes y regulaciones nacionales, tribales y estatales
          aplicables, así como con las políticas y procedimientos institucionales relevantes para el manejo de datos
          genómicos. Sin embargo, debido a que seqr se ejecuta dentro de los espacios de trabajo de Terra o AnVIL, no se
          requiere aprobación regulatoria adicional para usar seqr para analizar los datos almacenados en Terra o AnVIL.
          <br />

          Para obtener más información sobre cómo generar un conjunto denominado vcf, consulte esta &nbsp;
          <a href={VCF_DOCUMENTATION_URL} target="_blank" rel="noreferrer">documentación</a>
        </div>
      ),
    },
  }, {
    [ENGLISH]: {
      header: 'Q. Which browsers are supported for seqr?',
      content: `seqr is only supported in Google Chrome. While it may sometimes function in other browsers, to ensure 
      reliable behavior you should only use seqr in Chrome`,
    },
    [SPANISH]: {
      header: 'P: ¿Cuáles navegadores son compatibles con seqr?',
      content: `seqr solamente es compatible con Google Chrome. Aunque a veces puede funcionar en otros navegadores, 
      para garantizar un funcionamiento fiable sólo debe usar seqr en Chrome.`,
    },
  }, {
    [ENGLISH]: {
      header: 'Q. How can I set up seqr locally?',
      content: (
        <div>
          Setting up seqr locally generally requires strong bioinformatics skills to deploy, and also requires the
          download/storage of large annotation datasets. There is &nbsp;
          <a href="https://github.com/broadinstitute/seqr/blob/master/deploy/LOCAL_INSTALL.md" target="_blank" rel="noreferrer">documentation</a>
          &nbsp; in GitHub on setting up a local instance of seqr. If you have questions or issues with deployment, we
          recommend you take a look at our &nbsp;
          <a href="https://github.com/broadinstitute/seqr/discussions" target="_blank" rel="noreferrer">Github discussions page</a>
          &nbsp; for general troubleshooting help. If after looking into our documentation, you still have questions
          that
          can
          not be easily answered via a discussion post, send us an <a href="mailto:seqr@broadinstitute.org">email</a>.
        </div>
      ),
    },
    [SPANISH]: {
      header: 'P. ¿Cómo puedo configurar seqr localmente?',
      content: (
        <div>
          La configuración de seqr localmente generalmente requiere sólidas habilidades bioinformáticas para su
          implementación y también requiere la descarga/almacenamiento de grandes conjuntos de datos de anotaciones.
          Hay <a href="https://github.com/broadinstitute/seqr/blob/master/deploy/LOCAL_INSTALL.md" target="_blank" rel="noreferrer">documentación</a>
          &nbsp; en GitHub sobre cómo configurar una instancia local de seqr. Si tiene preguntas o problemas con la
          implementación, le recomendamos que consulte nuestra  &nbsp;
          <a href="https://github.com/broadinstitute/seqr/discussions" target="_blank" rel="noreferrer">página de debates de Github</a>
          &nbsp; para obtener ayuda general para la resolución de problemas. Si después de consultar nuestra
          documentación todavía tiene preguntas que no pueden responderse fácilmente a través de una publicación de
          discusión, envíenos un <a href="mailto:seqr@broadinstitute.org"> correo electrónico.</a>.
        </div>
      ),
    },
  }, {
    [ENGLISH]: {
      header: 'Q. I am unable to log in or access my project in seqr. What should I do?',
      content: (
        <div>
          To access seqr, users must have their email address registered with AnVIL (see instructions above) and to view
          specific projects they must have access to the AnVIL workspace corresponding to the project. The most frequent
          reason a user is unable to log in to a seqr project is because the email being used to log in is different
          from
          the one granted access to the project workspace. <br /><br />

          If you are still having trouble after you have confirmed your email address is registered with AnVIL and is
          the
          same as the one added to the seqr project, try the following:

          <List bulleted>
            <List.Item>
              <i>If you can not log into seqr at all:</i> Log into AnVIL first &nbsp;
              <a href="https://anvil.terra.bio" target="_blank" rel="noreferrer">here</a> and then proceed to &nbsp;
              <a href="https://seqr.broadinstitute.org" target="_blank" rel="noreferrer">seqr</a>.
            </List.Item>
            <List.Item>
              <i>If you do not see your project:</i> Log into AnVIL first &nbsp;
              <a href="https://anvil.terra.bio" target="_blank" rel="noreferrer">here</a>, navigate to the workspace
              associated with the project, then select &quot;Data&quot; &gt; &quot;Files&quot;
              &gt; &quot;Analyze in seqr&quot;.
            </List.Item>
          </List>
        </div>
      ),
    },
    [SPANISH]: {
      header: 'P. No puedo iniciar sesión o acceder a mi proyecto en seqr. ¿Qué debo hacer?',
      content: (
        <div>
          Para acceder a seqr, los usuarios deben tener su dirección de correo electrónico registrada en AnVIL (ver
          instrucciones arriba) y para ver proyectos específicos deben tener acceso al espacio de trabajo de AnVIL
          correspondiente al proyecto. La razón más frecuente por la que un usuario no puede iniciar sesión en un
          proyecto de seqr es porque el correo electrónico que se utiliza para iniciar sesión es diferente al que tiene
          acceso al espacio de trabajo del proyecto.<br /><br />

          Si aún tiene problemas después de haber confirmado que su dirección de correo electrónico está registrada con
          AnVIL y es la misma que se agregó al proyecto seqr, intente lo siguiente:

          <List bulleted>
            <List.Item>
              <i>Si no puede iniciar sesión en seqr en absoluto:</i> Primero inicie sesión en
              AnVIL <a href="https://anvil.terra.bio" target="_blank" rel="noreferrer">aquí</a> y luego proceda
              a <a href="https://seqr.broadinstitute.org" target="_blank" rel="noreferrer">seqr</a>.
            </List.Item>
            <List.Item>
              <i>Si no ve su proyecto:</i> Primero inicie sesión en
              AnVIL <a href="https://anvil.terra.bio" target="_blank" rel="noreferrer">aquí</a>, navegue hasta el
              espacio de trabajo asociado con el proyecto, luego seleccione &quot;Data&quot; &gt; &quot;Files&quot; &gt;
              &quot;Analyze in seqr&quot;.
            </List.Item>
          </List>
        </div>
      ),
    },
  }, {
    [ENGLISH]: {
      header: 'Q. How long does it take to load data in seqr?',
      content: `Genomic datasets are large and the seqr loading pipeline richly annotates the variants so data loading 
      can take from a few days to up to a week to process, depending on the sample numbers and data types.`,
    },
    [SPANISH]: {
      header: 'P. ¿Cuánto tiempo se tarda en cargar datos en seqr?',
      content: `Los conjuntos de datos genómicos son grandes y la canalización de carga de seqr anota detalladamente las
       variantes, por lo que la carga de datos puede tardar desde unos pocos días hasta una semana en procesarse, según
       el número de muestras y los tipos de datos.`,
    },
  }, {
    [ENGLISH]: {
      header: 'Q. How do I add a new team member to a project?',
      content: (
        <div>
          To add a new collaborator, navigate to the respective workspace in AnVIL and select &quot;Share&quot;. Only
          personnel with &quot;Can Share&quot; level access in AnVIL can add or remove collaborators. The seqr team does
          not manage user access. <br /><br />

          Please make sure your new team member registers the same email with Terra/AnVIL as the one added to the
          workspace. This is the most frequent reason why new users are unable to access a project.
        </div>
      ),
    },
    [SPANISH]: {
      header: 'P. ¿Cómo agrego un nuevo miembro del equipo a un proyecto?',
      content: (
        <div>
          Para agregar un nuevo colaborador, navegue al espacio de trabajo respectivo en AnVIL y seleccione
          &quot;Share&quot;. Solo el personal con nivel de acceso &quot;Can Share&quot; en AnVIL puede agregar o
          eliminar colaboradores. El equipo de seqr no gestiona el acceso de los usuarios. <br /><br />

          Asegúrese de que su nuevo miembro del equipo registre el mismo correo electrónico con Terra/AnVIL que el
          agregado al espacio de trabajo. Esta es la razón más frecuente por la que los nuevos usuarios no pueden
          acceder a un proyecto.
        </div>
      ),
    },
  }, {
    [ENGLISH]: {
      header: 'Q. What workspace permissions do I need to use seqr in AnVIL?',
      content: (
        <div>
          To access existing seqr projects, follow the above instructions for adding new collaborators. To submit a
          request to load data to seqr, you will need:<br />

          <List bulleted>
            {WORKSPACE_REQUIREMENTS.map(item => <List.Item>{item}</List.Item>)}
          </List>

          <br />
          If you do not have sufficient permissions on the workspace to request loading, you can contact the existing
          Owner of the workspace to request for these permissions. Another option is to clone the existing workspace and
          then request loading from the copy, as you will now be the Owner of the cloned workspace.
        </div>
      ),
    },
    [SPANISH]: {
      header: 'P. ¿Qué permisos de espacio de trabajo necesito para usar seqr en AnVIL?',
      content: (
        <div>
          Para acceder a proyectos existentes de seqr, siga las instrucciones anteriores para agregar nuevos
          colaboradores. Para enviar una solicitud para cargar datos a seqr, necesitará:<br />

          <List bulleted>
            <List.Item>Acceso de &quot;Writer&quot; o &quot;Owner&quot; al espacio de trabajo</List.Item>
            <List.Item>Permisos &quot;Can Share&quot; activados para el espacio de trabajo</List.Item>
            <List.Item>
              No hay &nbsp;
              <a href="https://support.terra.bio/hc/en-us/articles/360026775691" target="_blank" rel="noreferrer">
                dominios de autorización
              </a>
               &nbsp; para asociar con el espacio de trabajo
            </List.Item>
          </List>

          <br />
          Si no tiene permisos suficientes en el espacio de trabajo para solicitar la carga, puede comunicarse con el
          propietario existente del espacio de trabajo para solicitar estos permisos. Otra opción es clonar el espacio
          de trabajo existente y luego solicitar la carga desde la copia, ya que ahora será el propietario del espacio
          del espacio de trabajo clonado.
        </div>
      ),
    },
  }, {
    [ENGLISH]: {
      header: 'Q. How much does it cost to use seqr?',
      content: (
        <div>
          There are currently no costs associated with requests to load data from your AnVIL workspace to seqr or to use
          seqr in AnVIL to analyze genomic data. <br /><br />

          You will be responsible for the costs of storing your VCFs in an AnVIL workspace and will be responsible for
          any
          compute operations you choose to run in that workspace, including the cost for generating any joint called
          VCFs.
          You can find detailed information on AnVIL costs and billing &nbsp;
          <a href="https://support.terra.bio/hc/en-us/articles/360048632271-Overview-Terra-costs-and-billing-GCP-" target="_blank" rel="noreferrer">here</a>.
          Once it is confirmed that the data is accessible in seqr, the VCF can be removed from the AnVIL workspace.
        </div>
      ),
    },
    [SPANISH]: {
      header: 'P. ¿Cuánto cuesta usar seqr?',
      content: (
        <div>
          Actualmente no hay costos asociados con las solicitudes para cargar datos desde su espacio de trabajo de AnVIL
          a seqr o para usar seqr en AnVIL para analizar datos genómicos.<br /><br />

          Usted será responsable de los costos de almacenamiento de sus VCF en un espacio de trabajo de AnVIL y será
          responsable de cualquier operación de cómputo que elija ejecutar en ese espacio de trabajo, incluyendo el
          costo de generar cualquier conjunto denominado VCF. Puede encontrar información detallada sobre los costos y
          la facturación de AnVIL &nbsp;
          <a href="https://support.terra.bio/hc/en-us/articles/360048632271-Overview-Terra-costs-and-billing-GCP-" target="_blank" rel="noreferrer">aquí</a>.
          Una vez que se confirma que se puede acceder a los datos en seqr, el VCF se puede eliminar del espacio de
          trabajo de AnVIL.
        </div>
      ),
    },
  }, {
    [ENGLISH]: {
      header: 'Q. How do I add data to an existing project in seqr?',
      content: `To add new data, create a new joint called VCF with all the samples you want to include in your update. 
      This should include any new samples you want to add to the project and any of their family members which have been previously loaded. 
      Load this VCF using the Load Additional Data feature on the Project Page. All notes and tags saved in previously analyzed cases will be kept.`,
    },
    [SPANISH]: {
      header: 'P. ¿Cómo puedo agregar datos a un proyecto existente en seqr?',
      content: `Para agregar nuevos datos, crea un nuevo conjunto denominado VCF con todas las muestras que desea incluir en su actualización. 
      Esto debe incluir todas las muestras nuevas que desea agregar al proyecto y todos los miembros de la familia que se hayan cargado previamente. 
      Cargue este VCF utilizando la función Cargar datos adicionales en la página del proyecto. 
      Se conservarán todas las notas y etiquetas guardadas en los casos analizados previamente.`,
    },
  }, {
    [ENGLISH]: {
      header: 'Q. How do I transfer data between workspaces in seqr?',
      content: (
        <div>
          Each project in seqr is linked to a single workspace. We are unable to support loading a VCF from a new
          workspace to an existing seqr project. <br /><br />

          You can request to load a joint called VCF from a new workspace, which will create a new seqr project with the
          data. None of your previous analysis such as tags and notes will be available in this new project.
          Alternatively, if you want to add data to the existing project, you will need to move the new joint called VCF
          to the original workspace and request loading additional data from that project as described above.
        </div>
      ),
    },
    [SPANISH]: {
      header: 'P. ¿Cómo puedo transferir datos entre espacios de trabajo en seqr?',
      content: (
        <div>
          Cada proyecto en seqr está vinculado a un solo espacio de trabajo. No podemos admitir la carga de un VCF desde
          un nuevo espacio de trabajo a un proyecto seqr existente.<br /><br />

          Para cargar un nuevo conjunto denominado VCF, deberá solicitar la carga desde el nuevo espacio de trabajo.
          Esto creará un nuevo proyecto seqr con los datos, y ninguno de sus análisis anteriores, como etiquetas y
          notas, estará disponible allí. Alternativamente, si desea agregar datos al proyecto existente, deberá mover el
          nuevo conjunto denominado VCF a este espacio de trabajo original y solicitar la carga de datos adicionales
          desde allí.
        </div>
      ),
    },
  }, {
    [ENGLISH]: {
      header: 'Q. Who has access to my data in seqr?',
      content: (
        <div>
          A seqr project is accessible only to the person who requested the data loading and any additional members
          they add to the project through the AnVIL workspace. Members of the Broad Institute cannot access the project,
          except for a small number of engineers and the product owner on the seqr team,
          who may review the data if necessary. <br /><br />

          Non-identifiable information such as an individual’s affected status, high-level phenotype information,
          variant quality scores, and aggregate allele counts can be accessed by all seqr users through the
          Variant Lookup to aid in analysis.
        </div>
      ),
    },
    [SPANISH]: {
      header: 'P. ¿Quién tiene acceso a mis datos en seqr?',
      content: (
        <div>
          Un proyecto de seqr es accesible sólo a la persona que solicitó la carga de datos y cualquier miembro
          adicional que agregue al proyecto a través del espacio de trabajo AnVIL. Los miembros del Broad Institute
          no pueden acceder al proyecto, excepto una pequeña cantidad de ingenieros y el propietario del producto en el
          equipo seqr, quienes pueden revisar los datos si es necesario.<br /><br />

          Todos los usuarios de seqr pueden acceder a información no identificable, como el estado de afección de un
          individuo, información de fenotipo de alto nivel, puntajes de calidad de variantes y recuentos de alelos
          agregados, a través de la Búsqueda de variantes para ayudar en el análisis.
        </div>
      ),
    },
  }, {
    [ENGLISH]: {
      header: 'Q. How can I delete a project in seqr?',
      content: (
        <div>
          Before data has been loaded to a search project, the person who created the project can delete it from the
          seqr home page by selecting the hamburger menu on the right side of the project and selecting the delete
          project option. Once data has been loaded to a project, it can not be deleted. If you later learn that a
          sample does not have the appropriate permissions to be in seqr, you can reach out to us
          explaining the situation. <br /><br />

          Please note that deleting an AnVIL workspace does not remove its corresponding project from seqr;
          however, it will make it impossible for your team to access or manage the project in the future.
        </div>
      ),
    },
    [SPANISH]: {
      header: 'P. ¿Cómo puedo eliminar un proyecto de seqr?',
      content: (
        <div>
          Antes de que se hayan cargado los datos en un proyecto de búsqueda, la persona que creó el proyecto puede
          eliminarlo desde la página de inicio seleccionando el menú al lado derecho del proyecto y seleccionando la
          opción de eliminar proyecto. Una vez que se han cargado los datos en un proyecto, no se pueden eliminar.
          Si más adelante descubre que una muestra no tiene los permisos adecuados para estar en seqr,
          puede comunicarse con nosotros para explicar la situación.<br /><br />

          Tenga en cuenta que eliminando un espacio de trabajo de AnVIL no elimina su proyecto correspondiente de seqr;
          sin embargo, hará que sea imposible para su equipo acceder o administrar el proyecto en el futuro.
        </div>
      ),
    },
  }, {
    [ENGLISH]: {
      header: 'Q. Have ideas for seqr?',
      content: (
        <div>
          We are excited to see seqr&apos;s features grow to support your and others analysis needs, and welcome your
          suggestions or code contributions to the open source project. Please open a new &nbsp;
          <a href="https://github.com/broadinstitute/seqr/discussions" target="_blank" rel="noreferrer">Github discussion</a>
          &nbsp; to discuss your proposed ideas, or email us at <a href="mailto:seqr@broadinstitute.org">seqr@broadinstitute.org</a>.
        </div>
      ),
    },
    [SPANISH]: {
      header: 'P. ¿Tiene ideas para seqr?',
      content: (
        <div>
          Estamos emocionados de ver crecer las funciones de seqr para respaldar sus necesidades de análisis y las de
          otros, y agradecemos sus sugerencias o contribuciones de código al proyecto de open source. Abra una nueva
          &nbsp; <a href="https://github.com/broadinstitute/seqr/discussions" target="_blank" rel="noreferrer">discusión de Github</a>
          &nbsp; para discutir sus ideas, o envíenos un correo electrónico a &nbsp;
          <a href="mailto:seqr@broadinstitute.org">seqr@broadinstitute.org</a>.
        </div>
      ),
    },
  },
]

const LANGUAGES = [{ path: '', text: 'English' }, { path: SPANISH, text: 'Español' }]

const FaqPages = ({ match }) => (
  <Segment basic padded="very">
    <Header
      dividing
      size="huge"
      content="FAQ"
      subheader={LANGUAGES.map(({ path, text }) => (
        <ActiveDisabledNavLink key={path} exact padded activeColor="black" to={`/faq/${path}`}>{text}</ActiveDisabledNavLink>
      ))}
    />
    {FAQS.map((config) => {
      const { header, content } = config[match.params.language || ENGLISH]
      return [
        <Header content={header} size="medium" />,
        content,
      ]
    })}
  </Segment>
)

FaqPages.propTypes = {
  match: PropTypes.object,
}

export default FaqPages
