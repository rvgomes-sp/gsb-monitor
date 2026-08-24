export const ETAM_PROCESS_ID = "04892707000291-1-000011/2025";

export function calculateGuaranteeStack(guarantee) {
  const contractValue = Number(guarantee.contractValue) || 0;
  const executionPercent = Number(guarantee.executionPercent) || 0;
  const laborMinPercent = Number(guarantee.laborCoveragePercent?.min) || 0;
  const laborMaxPercent = Number(guarantee.laborCoveragePercent?.max) || laborMinPercent;
  const budgetValue = Number(guarantee.budgetValue) || 0;
  const proposalValue = Number(guarantee.proposalValue) || contractValue;
  const article59Threshold = budgetValue * 0.85;
  const article59Additional = budgetValue
    ? Math.max(0, article59Threshold - proposalValue)
    : 0;
  const executionAmount = contractValue * executionPercent / 100;
  const laborMinAmount = contractValue * laborMinPercent / 100;
  const laborMaxAmount = contractValue * laborMaxPercent / 100;

  return {
    executionAmount,
    laborMinAmount,
    laborMaxAmount,
    article59Threshold,
    article59Additional,
    minimumNominalCapacity: executionAmount + laborMinAmount + article59Additional,
    maximumNominalCapacity: executionAmount + laborMaxAmount + article59Additional,
    minimumTotalPercent: executionPercent + laborMinPercent,
    maximumTotalPercent: executionPercent + laborMaxPercent,
  };
}

export function observedPortfolioTotal(contracts = []) {
  return contracts.reduce((total, contract) => total + (Number(contract.value) || 0), 0);
}

export function sortApproachMap(contacts = []) {
  return [...contacts].sort((left, right) => Number(left.priority) - Number(right.priority));
}

export function assertCommercialCase(caseData) {
  if (!caseData?.processId) throw new Error("Dossiê sem identificador da contratação.");
  if (caseData.limitStatus === "SEM_LIMITE") {
    throw new Error("O motor não pode afirmar ausência de limite sem confirmação de seguradora.");
  }
  if (!caseData.flags?.includes("DIVERGENCIA_DOCUMENTAL")) {
    throw new Error("A divergência documental de cobertura deve permanecer visível.");
  }
  return true;
}

export function interpolateDraft(template, values = {}) {
  return String(template || "").replace(/\{\{(\w+)\}\}/g, (_, key) => values[key] || `[${key}]`);
}

