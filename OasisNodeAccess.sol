// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title OasisNodeAccess
 * @author Manus AI
 * @notice This contract manages access control for the Oasis API Aggregator nodes.
 * It defines an owner with priority access and allows the owner to grant
 * access to other addresses. This enables a simple on-chain authorization layer.
 */
contract OasisNodeAccess {
    // --- State Variables ---

    address public owner;
    string public constant CEN_MASTER_NODE = "Cen-Master";
    string public constant DANQIU_ALCHEMIST_NODE = "Danqiu-Alchemist";

    // Mapping from a user address to the node they have access to.
    // A user can have access to one, both, or none.
    mapping(address => mapping(string => bool)) public authorizedUsers;

    // --- Events ---

    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);
    event AccessGranted(address indexed user, string indexed node);
    event AccessRevoked(address indexed user, string indexed node);

    // --- Modifiers ---

    /**
     * @dev Throws if called by any account other than the owner.
     */
    modifier onlyOwner() {
        require(owner == msg.sender, "OasisAccess: caller is not the owner");
        _;
    }

    // --- Constructor ---

    /**
     * @dev Sets the contract deployer as the initial owner.
     * The owner gets automatic access to both nodes.
     */
    constructor() {
        owner = msg.sender;
        authorizedUsers[owner][CEN_MASTER_NODE] = true;
        authorizedUsers[owner][DANQIU_ALCHEMIST_NODE] = true;
        emit OwnershipTransferred(address(0), owner);
        emit AccessGranted(owner, CEN_MASTER_NODE);
        emit AccessGranted(owner, DANQIU_ALCHEMIST_NODE);
    }

    // --- Owner Functions ---

    /**
     * @notice Grants access to a specific node for a given user address.
     * @dev Can only be called by the contract owner.
     * @param _user The address of the user to grant access to.
     * @param _node The name of the node (e.g., "Cen-Master").
     */
    function grantAccess(address _user, string calldata _node) external onlyOwner {
        require(_user != address(0), "OasisAccess: invalid user address");
        require(
            keccak256(abi.encodePacked(_node)) == keccak256(abi.encodePacked(CEN_MASTER_NODE)) ||
            keccak256(abi.encodePacked(_node)) == keccak256(abi.encodePacked(DANQIU_ALCHEMIST_NODE)),
            "OasisAccess: node does not exist"
        );
        authorizedUsers[_user][_node] = true;
        emit AccessGranted(_user, _node);
    }

    /**
     * @notice Revokes access from a specific node for a given user address.
     * @dev Can only be called by the contract owner.
     * @param _user The address of the user to revoke access from.
     * @param _node The name of the node.
     */
    function revokeAccess(address _user, string calldata _node) external onlyOwner {
        require(owner != _user, "OasisAccess: cannot revoke access from owner");
        authorizedUsers[_user][_node] = false;
        emit AccessRevoked(_user, _node);
    }

    /**
     * @notice Transfers ownership of the contract to a new account.
     * @dev Can only be called by the current owner.
     * The new owner will automatically receive access to both nodes.
     */
    function transferOwnership(address newOwner) public onlyOwner {
        require(newOwner != address(0), "OasisAccess: new owner is the zero address");
        emit OwnershipTransferred(owner, newOwner);
        owner = newOwner;
        
        // Grant new owner access if they don't have it already
        if (!authorizedUsers[newOwner][CEN_MASTER_NODE]) {
            authorizedUsers[newOwner][CEN_MASTER_NODE] = true;
            emit AccessGranted(newOwner, CEN_MASTER_NODE);
        }
        if (!authorizedUsers[newOwner][DANQIU_ALCHEMIST_NODE]) {
            authorizedUsers[newOwner][DANQIU_ALCHEMIST_NODE] = true;
            emit AccessGranted(newOwner, DANQIU_ALCHEMIST_NODE);
        }
    }

    // --- View Functions ---

    /**
     * @notice Checks if a user is authorized to access a specific node.
     * @dev Returns true if the user has been granted access to the specified node.
     * The owner always has access.
     * @param _user The address to check.
     * @param _node The node to check access for.
     * @return bool True if the user has access, false otherwise.
     */
    function isAuthorized(address _user, string calldata _node) external view returns (bool) {
        return authorizedUsers[_user][_node];
    }
}
